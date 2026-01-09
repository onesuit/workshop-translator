# Reviewer 에이전트 - 품질 검토
# Librarian 패턴 참고: 증거 기반, 구체적 피드백
# Translator 패턴 적용: Agent 기반 + 병렬 처리 + task 업데이트

import os
import threading
from strands import Agent, tool
from strands_tools import file_read, file_write
from model.load import load_sonnet
from prompts.system_prompts import REVIEWER_PROMPT
from tools.file_tools import read_workshop_file


def create_reviewer_agent() -> Agent:
    """
    Reviewer 에이전트 인스턴스를 생성합니다.
    
    Agent는 품질 검토와 함께 tasks.md를 읽고 업데이트할 수 있습니다.
    
    Returns:
        Agent: Reviewer 에이전트 인스턴스
    """
    return Agent(
        model=load_sonnet(),
        system_prompt=REVIEWER_PROMPT,
        tools=[file_read, file_write],  # tasks.md 읽기/쓰기 가능
    )


def basic_review_checks(
    source_path: str,
    target_path: str,
    source_content: str,
    target_content: str,
) -> dict:
    """
    기본 검토 체크를 수행합니다 (Agent 없이 빠른 검증).
    
    이 함수는 review_file 내부에서 사용되며, Agent가 도구로 활용할 수 있습니다.
    
    Args:
        source_path: 원본 파일 경로
        target_path: 번역 파일 경로
        source_content: 원본 파일 내용
        target_content: 번역 파일 내용
    
    Returns:
        dict: 기본 검토 결과
    """
    issues = []
    score = 100
    
    # 1. Frontmatter 확인
    if not target_content.startswith("---"):
        issues.append("Frontmatter가 없습니다")
        score -= 20
    
    # 2. 줄 수 비교
    source_lines = len(source_content.split("\n"))
    target_lines = len(target_content.split("\n"))
    line_diff = abs(target_lines - source_lines) / source_lines * 100
    
    if line_diff > 20:
        issues.append(f"줄 수 차이가 큽니다: {line_diff:.1f}%")
        score -= 15
    elif line_diff > 10:
        issues.append(f"줄 수 차이: {line_diff:.1f}%")
        score -= 5
    
    # 3. 코드 블록 보존 확인
    source_code_blocks = source_content.count("```")
    target_code_blocks = target_content.count("```")
    
    if source_code_blocks != target_code_blocks:
        issues.append(f"코드 블록 수 불일치: 원본 {source_code_blocks}, 번역 {target_code_blocks}")
        score -= 10
    
    # 4. AWS 서비스명 확인 (영어 유지 여부)
    aws_services = ["Amazon SES", "AWS Lambda", "Amazon S3", "Amazon EC2", "AWS IAM"]
    for service in aws_services:
        if service in source_content and service not in target_content:
            issues.append(f"AWS 서비스명이 변경됨: {service}")
            score -= 5
    
    # 5. 링크 보존 확인
    import re
    source_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', source_content)
    target_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', target_content)
    
    source_urls = set(url for _, url in source_links)
    target_urls = set(url for _, url in target_links)
    
    missing_urls = source_urls - target_urls
    if missing_urls:
        issues.append(f"누락된 링크: {len(missing_urls)}개")
        score -= 5
    
    # 점수 보정
    score = max(0, min(100, score))
    
    return {
        "score": score,
        "issues": issues,
        "line_diff_percent": round(line_diff, 2),
    }


@tool
def review_file(
    source_path: str,
    target_path: str,
    target_lang: str,
    tasks_path: str = None,
    task_id: str = None,
    source_lang: str = "en",
) -> dict:
    """
    단일 파일의 번역 품질을 검토합니다.
    
    이 도구는 Orchestrator가 단일 파일 검토가 필요할 때 직접 호출하거나,
    review_files_parallel 내부에서 각 파일을 검토할 때 사용됩니다.
    내부에서 Reviewer Agent를 실행하여 번역 품질을 평가합니다.
    
    Agent는 tasks.md를 읽고 자신의 작업 상태를 업데이트할 수 있습니다.
    
    Args:
        source_path: 원본 파일 경로
        target_path: 번역 파일 경로
        target_lang: 타겟 언어 코드
        tasks_path: tasks.md 파일 경로 (선택, Agent가 상태 업데이트용)
        task_id: 태스크 ID (선택, 예: "2.1.2")
        source_lang: 소스 언어 코드 (기본: en)
    
    Returns:
        dict: 검토 결과
            - source_path: 원본 파일 경로
            - target_path: 번역 파일 경로
            - success: 성공 여부
            - score: 품질 점수 (0-100)
            - status: PASS/FAIL
            - issues: 발견된 문제 목록
            - summary: 요약
            - line_diff_percent: 줄 수 차이 비율
            - error: 에러 메시지 (실패 시)
    """
    try:
        # 파일 읽기
        source_content = read_workshop_file(source_path)
        target_content = read_workshop_file(target_path)
        
        # 기본 검토 수행
        basic_result = basic_review_checks(source_path, target_path, source_content, target_content)
        
        # Agent 생성 및 실행
        agent = create_reviewer_agent()
        
        # 언어 이름 매핑
        lang_names = {
            "en": "English",
            "ko": "한국어",
            "ja": "日本語",
            "zh": "中文",
            "es": "Español",
            "fr": "Français",
            "de": "Deutsch",
            "pt": "Português",
        }
        source_lang_name = lang_names.get(source_lang, source_lang)
        target_lang_name = lang_names.get(target_lang, target_lang)
        
        # tasks.md 정보 포함
        tasks_info = ""
        if tasks_path and task_id:
            # task_id에서 파일 번호 추출 (예: "2.1.2" -> "2.1")
            file_task_id = ".".join(task_id.split(".")[:2])
            translate_task_id = f"{file_task_id}.1"
            
            tasks_info = f"""

## 작업 추적 및 의존성
- tasks.md 경로: {tasks_path}
- 현재 태스크 ID: {task_id} (품질 검토)
- 선행 태스크 ID: {translate_task_id} (번역)

**중요 - 의존성 체크**:
1. 먼저 tasks.md를 읽어서 선행 태스크 {translate_task_id}의 상태를 확인하세요.
2. 선행 태스크가 `[x]` (완료)가 아니면 검토를 진행하지 마세요.
3. 선행 태스크가 완료되었으면:
   - 검토 시작 전: 태스크 {task_id}를 `[~]`로 변경
   - 검토 완료 후: 태스크 {task_id}를 `[x]`로 변경
   - 검토 실패 시: 태스크 {task_id}를 `[ ]`로 되돌림

체크박스 상태:
- `[ ]` = 미완료 (Not Started)
- `[~]` = 진행 중 (In Progress)
- `[x]` = 완료 (Completed)

**선행 작업이 완료되지 않았을 경우**:
"선행 작업(번역)이 완료되지 않아 검토를 진행할 수 없습니다."라고 응답하세요.
"""
        
        prompt = f"""
다음 번역 파일의 품질을 검토해주세요.

## 파일 정보
- 원본: {source_path} ({source_lang_name})
- 번역: {target_path} ({target_lang_name})

## 기본 검토 결과
- 점수: {basic_result['score']}/100
- 발견된 문제: {basic_result['issues']}
- 줄 수 차이: {basic_result['line_diff_percent']}%

## 원본 내용 (처음 500자)
<source>
{source_content[:500]}
</source>

## 번역 내용 (처음 500자)
<target>
{target_content[:500]}
</target>

## 검토 항목
1. AWS 용어 일관성 (서비스명은 영어 유지)
2. 기술 용어 정확성
3. 문장 자연스러움
4. Markdown 구조 유지
{tasks_info}

기본 검토 결과를 바탕으로 추가 문제가 있는지 확인하고, 최종 점수와 상태(PASS/FAIL)를 결정해주세요.
80점 이상이면 PASS, 미만이면 FAIL입니다.

응답 형식:
- 최종 점수: [점수]/100
- 상태: PASS 또는 FAIL
- 추가 발견 문제: [문제 목록]
- 요약: [한 줄 요약]
"""
        
        response = agent(prompt)
        agent_feedback = str(response).strip()
        
        # Agent 응답에서 점수 추출 시도
        import re
        score_match = re.search(r'최종 점수[:\s]*(\d+)', agent_feedback)
        if score_match:
            final_score = int(score_match.group(1))
        else:
            # Agent가 점수를 제공하지 않으면 기본 검토 점수 사용
            final_score = basic_result['score']
        
        # Agent 응답에서 상태 추출 시도
        status = "PASS" if final_score >= 80 else "FAIL"
        if "FAIL" in agent_feedback.upper():
            status = "FAIL"
        elif "PASS" in agent_feedback.upper():
            status = "PASS"
        
        return {
            "source_path": source_path,
            "target_path": target_path,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "success": True,
            "score": final_score,
            "status": status,
            "issues": basic_result['issues'],
            "summary": f"품질 점수: {final_score}/100 ({status})",
            "line_diff_percent": basic_result['line_diff_percent'],
            "agent_feedback": agent_feedback,
        }
        
    except Exception as e:
        return {
            "source_path": source_path,
            "target_path": target_path,
            "success": False,
            "score": 0,
            "status": "ERROR",
            "issues": [str(e)],
            "summary": f"검토 실패: {str(e)}",
            "error": str(e),
        }


@tool
def review_files_parallel(
    files: list,
    target_lang: str,
    tasks_path: str,
    source_lang: str = "en",
    max_concurrent: int = 5,
) -> dict:
    """
    여러 파일을 병렬로 검토합니다.
    
    이 도구는 Orchestrator가 다중 파일 검토가 필요할 때 호출합니다.
    Threading과 Semaphore를 사용하여 여러 파일을 동시에 검토하며,
    각 스레드에서 독립적으로 Reviewer Agent를 실행합니다.
    
    **워크플로우**:
    1. 이 도구 호출 → 백그라운드 스레드 시작 → 즉시 반환
    2. check_background_tasks로 진행 상황 확인
    3. tasks.md 파일에서 완료 상태 추적
    
    Args:
        files: 검토 대상 파일 목록 (원본 파일 경로)
        target_lang: 타겟 언어 코드 (ko, ja, zh 등)
        tasks_path: tasks.md 파일 경로
        source_lang: 소스 언어 코드 (기본: en)
        max_concurrent: 최대 동시 실행 수 (기본: 5)
    
    Returns:
        dict: 검토 시작 결과 (즉시 반환)
            - status: "started"
            - total: 전체 파일 수
            - max_concurrent: 최대 동시 실행 수
            - tasks: 시작된 태스크 정보 목록
            - message: 상태 메시지
    """
    # 순환 import 방지를 위해 함수 내부에서 import
    from main import app
    
    # 세마포어로 동시 실행 수 제어
    semaphore = threading.Semaphore(max_concurrent)
    started_tasks = []
    
    def review_worker(source_path: str, task_id: str, internal_task_id: str):
        """
        백그라운드 검토 작업을 수행하는 워커 함수.
        각 워커는 독립적으로 Reviewer Agent를 생성하고 실행합니다.
        Agent가 tasks.md를 직접 읽고 업데이트합니다.
        """
        with semaphore:  # 최대 max_concurrent개만 동시 실행
            try:
                # 타겟 파일 경로 생성
                target_path = source_path.replace(f".{source_lang}.md", f".{target_lang}.md")
                
                # review_file 도구 함수 호출 (Agent가 tasks.md 업데이트)
                result = review_file(
                    source_path, 
                    target_path, 
                    target_lang,
                    tasks_path=tasks_path,
                    task_id=task_id,
                    source_lang=source_lang
                )
                
            except Exception as e:
                print(f"검토 실패 ({source_path}): {e}")
            
            finally:
                # AgentCore 태스크 완료 표시
                app.complete_async_task(internal_task_id)
    
    # 각 파일에 대해 백그라운드 스레드 시작
    for i, source_path in enumerate(files):
        # tasks.md의 태스크 ID 생성 (예: "2.1.2", "2.2.2", ...)
        task_id = f"2.{i+1}.2"
        
        # AgentCore 백그라운드 태스크 추적 시작
        internal_task_id = app.add_async_task("review", {
            "file": source_path,
            "task_id": task_id,
            "target_lang": target_lang
        })
        
        # 백그라운드 스레드 시작
        threading.Thread(
            target=review_worker,
            args=(source_path, task_id, internal_task_id),
            daemon=True
        ).start()
        
        started_tasks.append({
            "file": source_path,
            "task_id": task_id,
            "internal_task_id": internal_task_id
        })
    
    return {
        "status": "started",
        "total": len(files),
        "max_concurrent": max_concurrent,
        "tasks": started_tasks,
        "message": f"{len(files)}개 파일 검토 시작 (최대 {max_concurrent}개 동시 실행)"
    }


@tool
def review_all_translations(
    source_files: list,
    target_lang: str,
    tasks_path: str = None,
) -> dict:
    """
    모든 번역 파일의 품질을 검토합니다 (순차 실행).
    
    병렬 처리가 필요한 경우 review_files_parallel을 사용하세요.
    
    Args:
        source_files: 원본 파일 목록
        target_lang: 타겟 언어 코드
        tasks_path: tasks.md 파일 경로 (선택)
    
    Returns:
        dict: 전체 검토 결과
    """
    results = []
    total_score = 0
    pass_count = 0
    fail_count = 0
    
    for i, source_path in enumerate(source_files):
        target_path = source_path.replace(".en.md", f".{target_lang}.md")
        
        # tasks.md의 검토 태스크 ID (예: "2.1.2", "2.2.2", ...)
        task_id = f"2.{i+1}.2" if tasks_path else None
        
        if os.path.exists(target_path):
            result = review_file(
                source_path, 
                target_path, 
                target_lang,
                tasks_path=tasks_path,
                task_id=task_id
            )
            results.append(result)
            
            if result.get("success"):
                total_score += result["score"]
                
                if result["status"] == "PASS":
                    pass_count += 1
                else:
                    fail_count += 1
            else:
                fail_count += 1
        else:
            results.append({
                "source_path": source_path,
                "target_path": target_path,
                "success": False,
                "score": 0,
                "status": "MISSING",
                "issues": ["번역 파일이 없습니다"],
            })
            fail_count += 1
    
    avg_score = total_score / len(results) if results else 0
    
    return {
        "total": len(results),
        "pass": pass_count,
        "fail": fail_count,
        "average_score": round(avg_score, 2),
        "overall_status": "PASS" if fail_count == 0 else "FAIL",
        "results": results,
    }

# Validator 에이전트 - 구조 검증
# Explore 패턴 참고: 빠른 검증, 명확한 결과
# Translator 패턴 적용: Agent 기반 + 병렬 처리 + task 업데이트

import os
import re
import threading
from strands import Agent, tool
from strands_tools import file_read, file_write
from model.load import load_haiku
from prompts.system_prompts import VALIDATOR_PROMPT
from tools.file_tools import (
    read_workshop_file,
    compare_line_counts,
)


def create_validator_agent() -> Agent:
    """
    Validator 에이전트 인스턴스를 생성합니다.
    
    Agent는 구조 검증과 함께 tasks.md를 읽고 업데이트할 수 있습니다.
    
    Returns:
        Agent: Validator 에이전트 인스턴스
    """
    return Agent(
        model=load_haiku(),
        system_prompt=VALIDATOR_PROMPT,
        tools=[file_read, file_write],  # tasks.md 읽기/쓰기 가능
    )


def validate_frontmatter(content: str) -> dict:
    """
    Frontmatter를 검증합니다.
    
    Args:
        content: 파일 내용
    
    Returns:
        dict: 검증 결과
    """
    errors = []
    warnings = []
    
    # Frontmatter 존재 확인
    if not content.startswith("---"):
        errors.append("Frontmatter가 없습니다")
        return {"valid": False, "errors": errors, "warnings": warnings}
    
    # Frontmatter 추출
    parts = content.split("---", 2)
    if len(parts) < 3:
        errors.append("Frontmatter 형식이 잘못되었습니다")
        return {"valid": False, "errors": errors, "warnings": warnings}
    
    frontmatter = parts[1].strip()
    
    # 필수 필드 확인
    if "title:" not in frontmatter:
        errors.append("title 필드가 없습니다")
    
    if "weight:" not in frontmatter:
        warnings.append("weight 필드가 없습니다")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def validate_markdown_syntax(content: str) -> dict:
    """
    Markdown 구문을 검증합니다.
    
    Args:
        content: 파일 내용
    
    Returns:
        dict: 검증 결과
    """
    errors = []
    warnings = []
    
    # 코드 블록 짝 확인
    code_block_count = content.count("```")
    if code_block_count % 2 != 0:
        errors.append("코드 블록이 닫히지 않았습니다")
    
    # 링크 형식 확인
    broken_links = re.findall(r'\[([^\]]*)\]\([^)]*\n', content, re.MULTILINE)
    if broken_links:
        errors.append(f"깨진 링크가 있습니다: {len(broken_links)}개")
    
    # 이미지 형식 확인
    broken_images = re.findall(r'!\[([^\]]*)\]\([^)]*\n', content, re.MULTILINE)
    if broken_images:
        errors.append(f"깨진 이미지 링크가 있습니다: {len(broken_images)}개")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def basic_validation_checks(
    source_path: str,
    target_path: str,
    target_content: str,
) -> dict:
    """
    기본 검증 체크를 수행합니다 (Agent 없이 빠른 검증).
    
    이 함수는 validate_file 내부에서 사용되며, Agent가 도구로 활용할 수 있습니다.
    
    Args:
        source_path: 원본 파일 경로
        target_path: 번역 파일 경로
        target_content: 번역 파일 내용
    
    Returns:
        dict: 기본 검증 결과
    """
    errors = []
    warnings = []
    
    # Frontmatter 검증
    fm_result = validate_frontmatter(target_content)
    errors.extend(fm_result["errors"])
    warnings.extend(fm_result["warnings"])
    
    # Markdown 구문 검증
    md_result = validate_markdown_syntax(target_content)
    errors.extend(md_result["errors"])
    warnings.extend(md_result["warnings"])
    
    # 줄 수 비교
    line_result = compare_line_counts(source_path, target_path)
    line_diff = line_result["diff_percent"]
    
    if line_diff > 20:
        errors.append(f"줄 수 차이가 큽니다 ({line_diff:.1f}%)")
    elif line_diff > 10:
        warnings.append(f"줄 수 차이 {line_diff:.1f}%")
    
    return {
        "errors": errors,
        "warnings": warnings,
        "line_diff_percent": line_diff,
    }


@tool
def validate_file(
    source_path: str,
    target_lang: str,
    tasks_path: str = None,
    task_id: str = None,
    source_lang: str = "en",
) -> dict:
    """
    단일 파일의 구조를 검증합니다.
    
    이 도구는 Orchestrator가 단일 파일 검증이 필요할 때 직접 호출하거나,
    validate_files_parallel 내부에서 각 파일을 검증할 때 사용됩니다.
    내부에서 Validator Agent를 실행하여 구조적 정확성을 확인합니다.
    
    Agent는 tasks.md를 읽고 자신의 작업 상태를 업데이트할 수 있습니다.
    
    Args:
        source_path: 원본 파일 경로
        target_lang: 타겟 언어 코드
        tasks_path: tasks.md 파일 경로 (선택, Agent가 상태 업데이트용)
        task_id: 태스크 ID (선택, 예: "2.1.3")
        source_lang: 소스 언어 코드 (기본: en)
    
    Returns:
        dict: 검증 결과
            - source_path: 원본 파일 경로
            - target_path: 번역 파일 경로
            - success: 성공 여부
            - status: PASS/FAIL
            - errors: 오류 목록
            - warnings: 경고 목록
            - line_diff_percent: 줄 수 차이 비율
            - error: 에러 메시지 (실패 시)
    """
    target_path = source_path.replace(f".{source_lang}.md", f".{target_lang}.md")
    
    try:
        # 파일 존재 확인
        if not os.path.exists(target_path):
            return {
                "source_path": source_path,
                "target_path": target_path,
                "success": False,
                "status": "MISSING",
                "errors": ["번역 파일이 없습니다"],
                "warnings": [],
                "error": "File not found",
            }
        
        # 파일 읽기
        target_content = read_workshop_file(target_path)
        
        # tasks.md 상태 업데이트: 진행 중으로 변경
        if tasks_path and task_id:
            from agents.task_planner import update_task_status
            update_task_status(tasks_path, task_id, "in_progress")
        
        # 기본 검증 수행
        basic_result = basic_validation_checks(source_path, target_path, target_content)
        
        # Agent 생성 및 실행
        agent = create_validator_agent()
        
        # tasks.md 정보 포함
        tasks_info = ""
        if tasks_path and task_id:
            # task_id에서 파일 번호 추출 (예: "2.1.3" -> "2.1")
            file_task_id = ".".join(task_id.split(".")[:2])
            translate_task_id = f"{file_task_id}.1"
            review_task_id = f"{file_task_id}.2"
            
            tasks_info = f"""

## 작업 추적 및 의존성
- tasks.md 경로: {tasks_path}
- 현재 태스크 ID: {task_id} (구조 검증)
- 선행 태스크 ID: {translate_task_id} (번역), {review_task_id} (품질 검토)

**중요 - 의존성 체크**:
1. 먼저 tasks.md를 읽어서 선행 태스크들의 상태를 확인하세요:
   - {translate_task_id} (번역) 상태
   - {review_task_id} (품질 검토) 상태
2. 두 선행 태스크가 모두 `[x]` (완료)가 아니면 검증을 진행하지 마세요.
3. 선행 태스크들이 모두 완료되었으면:
   - 검증 시작 전: 태스크 {task_id}를 `[~]`로 변경
   - 검증 완료 후: 태스크 {task_id}를 `[x]`로 변경
   - 검증 실패 시: 태스크 {task_id}를 `[ ]`로 되돌림

체크박스 상태:
- `[ ]` = 미완료 (Not Started)
- `[~]` = 진행 중 (In Progress)
- `[x]` = 완료 (Completed)

**선행 작업이 완료되지 않았을 경우**:
"선행 작업(번역 및 검토)이 완료되지 않아 검증을 진행할 수 없습니다."라고 응답하세요.
"""
        
        prompt = f"""
다음 번역 파일의 구조를 검증해주세요.

## 파일 정보
- 원본: {source_path}
- 번역: {target_path}

## 기본 검증 결과
- 오류: {basic_result['errors']}
- 경고: {basic_result['warnings']}
- 줄 수 차이: {basic_result['line_diff_percent']:.1f}%

## 번역 파일 내용 (처음 500자)
<content>
{target_content[:500]}
</content>

## 검증 항목
1. Frontmatter 필수 필드 (title, weight)
2. Markdown 구문 오류
3. 코드 블록 짝 맞춤
4. 링크 형식 정확성
{tasks_info}

기본 검증 결과를 바탕으로 추가 문제가 있는지 확인하고, 최종 상태(PASS/FAIL)를 결정해주세요.
오류가 없으면 PASS, 오류가 있으면 FAIL입니다.

응답 형식:
- 상태: PASS 또는 FAIL
- 추가 발견 오류: [오류 목록]
- 추가 발견 경고: [경고 목록]
- 요약: [한 줄 요약]
"""
        
        response = agent(prompt)
        agent_feedback = str(response).strip()
        
        # Agent 응답에서 상태 추출 시도
        status = "PASS" if len(basic_result['errors']) == 0 else "FAIL"
        if "FAIL" in agent_feedback.upper():
            status = "FAIL"
        elif "PASS" in agent_feedback.upper():
            status = "PASS"
        
        # tasks.md 상태 업데이트: 완료로 변경
        if tasks_path and task_id:
            from agents.task_planner import update_task_status
            update_task_status(tasks_path, task_id, "completed")
        
        return {
            "source_path": source_path,
            "target_path": target_path,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "success": True,
            "status": status,
            "errors": basic_result['errors'],
            "warnings": basic_result['warnings'],
            "line_diff_percent": round(basic_result['line_diff_percent'], 2),
            "agent_feedback": agent_feedback,
        }
        
    except Exception as e:
        # tasks.md 상태 업데이트: 실패 시 미완료로 되돌림
        if tasks_path and task_id:
            from agents.task_planner import update_task_status
            update_task_status(tasks_path, task_id, "not_started")
        
        return {
            "source_path": source_path,
            "target_path": target_path,
            "success": False,
            "status": "ERROR",
            "errors": [str(e)],
            "warnings": [],
            "error": str(e),
        }


@tool
def validate_files_parallel(
    files: list,
    target_lang: str,
    tasks_path: str,
    source_lang: str = "en",
    max_concurrent: int = 5,
) -> dict:
    """
    여러 파일을 병렬로 검증합니다.
    
    이 도구는 Orchestrator가 다중 파일 검증이 필요할 때 호출합니다.
    Threading과 Semaphore를 사용하여 여러 파일을 동시에 검증하며,
    각 스레드에서 독립적으로 Validator Agent를 생성하고 실행합니다.
    
    **워크플로우**:
    1. 이 도구 호출 → 백그라운드 스레드 시작 → 즉시 반환
    2. check_background_tasks로 진행 상황 확인
    3. tasks.md 파일에서 완료 상태 추적
    
    Args:
        files: 검증 대상 파일 목록 (원본 파일 경로)
        target_lang: 타겟 언어 코드 (ko, ja, zh 등)
        tasks_path: tasks.md 파일 경로
        source_lang: 소스 언어 코드 (기본: en)
        max_concurrent: 최대 동시 실행 수 (기본: 5)
    
    Returns:
        dict: 검증 시작 결과 (즉시 반환)
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
    
    def validate_worker(source_path: str, task_id: str, internal_task_id: str):
        """
        백그라운드 검증 작업을 수행하는 워커 함수.
        각 워커는 독립적으로 Validator Agent를 생성하고 실행합니다.
        Agent가 tasks.md를 직접 읽고 업데이트합니다.
        """
        with semaphore:  # 최대 max_concurrent개만 동시 실행
            try:
                # validate_file 도구 함수 호출 (Agent가 tasks.md 업데이트)
                result = validate_file(
                    source_path, 
                    target_lang,
                    tasks_path=tasks_path,
                    task_id=task_id,
                    source_lang=source_lang
                )
                
            except Exception as e:
                print(f"검증 실패 ({source_path}): {e}")
            
            finally:
                # AgentCore 태스크 완료 표시
                app.complete_async_task(internal_task_id)
    
    # 각 파일에 대해 백그라운드 스레드 시작
    for i, source_path in enumerate(files):
        # tasks.md의 태스크 ID 생성 (예: "2.1.3", "2.2.3", ...)
        task_id = f"2.{i+1}.3"
        
        # AgentCore 백그라운드 태스크 추적 시작
        internal_task_id = app.add_async_task("validate", {
            "file": source_path,
            "task_id": task_id,
            "target_lang": target_lang
        })
        
        # 백그라운드 스레드 시작
        threading.Thread(
            target=validate_worker,
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
        "message": f"{len(files)}개 파일 검증 시작 (최대 {max_concurrent}개 동시 실행)"
    }


@tool
def validate_structure(
    source_files: list,
    target_lang: str,
    tasks_path: str = None,
) -> dict:
    """
    번역된 파일들의 구조를 검증합니다 (순차 실행).
    
    병렬 처리가 필요한 경우 validate_files_parallel을 사용하세요.
    
    Args:
        source_files: 원본 파일 목록
        target_lang: 타겟 언어 코드
        tasks_path: tasks.md 파일 경로 (선택)
    
    Returns:
        dict: 검증 결과
            - status: PASS/FAIL
            - coverage: 번역 커버리지
            - coverage_percent: 커버리지 퍼센트
            - line_diff_avg: 평균 줄 수 차이
            - errors: 오류 목록
            - warnings: 경고 목록
            - error_count: 오류 수
            - warning_count: 경고 수
    """
    errors = []
    warnings = []
    translated_count = 0
    total_line_diff = 0
    
    for i, source_path in enumerate(source_files):
        # tasks.md의 검증 태스크 ID (예: "2.1.3", "2.2.3", ...)
        task_id = f"2.{i+1}.3" if tasks_path else None
        
        result = validate_file(
            source_path, 
            target_lang,
            tasks_path=tasks_path,
            task_id=task_id
        )
        
        if result.get("success"):
            translated_count += 1
            errors.extend(result.get("errors", []))
            warnings.extend(result.get("warnings", []))
            total_line_diff += result.get("line_diff_percent", 0)
        else:
            errors.extend(result.get("errors", []))
    
    # 결과 집계
    total_files = len(source_files)
    coverage = translated_count / total_files * 100 if total_files > 0 else 0
    avg_line_diff = total_line_diff / translated_count if translated_count > 0 else 0
    
    status = "PASS" if len(errors) == 0 and coverage == 100 else "FAIL"
    
    return {
        "status": status,
        "coverage": f"{translated_count}/{total_files} files ({coverage:.1f}%)",
        "coverage_percent": round(coverage, 2),
        "line_diff_avg": round(avg_line_diff, 2),
        "errors": errors,
        "warnings": warnings,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }


# =============================================================================
# 참고용 함수 (필요시 사용)
# =============================================================================

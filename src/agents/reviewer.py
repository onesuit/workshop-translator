# Reviewer 에이전트 - 품질 검토
# Librarian 패턴 참고: 증거 기반, 구체적 피드백

import os
from strands import Agent, tool
from strands_tools import file_read
from model.load import load_sonnet
from prompts.system_prompts import REVIEWER_PROMPT
from tools.file_tools import read_workshop_file


def create_reviewer_agent() -> Agent:
    """
    Reviewer 에이전트 인스턴스를 생성합니다.
    
    Agent는 다음 도구들을 사용할 수 있습니다:
    - file_read: 파일 내용 읽기 (strands 기본 도구)
    
    Returns:
        Agent: Reviewer 에이전트 인스턴스
    """
    return Agent(
        model=load_sonnet(),
        system_prompt=REVIEWER_PROMPT,
        tools=[file_read],
    )


@tool
def review_translation(
    source_path: str,
    target_path: str,
    target_lang: str,
    tasks_path: str = None,
    task_id: str = None,
) -> dict:
    """
    번역 품질을 검토합니다.
    
    이 도구는 Orchestrator가 호출하며, 내부에서 Reviewer Agent를 실행합니다.
    Agent는 LLM을 사용하여 번역 품질을 평가하고 구체적인 피드백을 제공합니다.
    
    Args:
        source_path: 원본 파일 경로
        target_path: 번역 파일 경로
        target_lang: 타겟 언어 코드
        tasks_path: tasks.md 파일 경로 (선택)
        task_id: 태스크 ID (선택, tasks.md 업데이트용)
    
    Returns:
        dict: 검토 결과
            - file: 파일 경로
            - score: 품질 점수 (0-100)
            - status: PASS/FAIL
            - issues: 발견된 문제 목록
            - summary: 요약
            - line_diff_percent: 줄 수 차이 비율
            - source_lines: 원본 줄 수
            - target_lines: 번역 줄 수
    """
    # tasks.md 업데이트 (검토 시작)
    if tasks_path and task_id:
        from agents.task_planner import update_task_status
        update_task_status(tasks_path, task_id, status="in_progress")
    
    try:
        # 파일 읽기
        source_content = read_workshop_file(source_path)
        target_content = read_workshop_file(target_path)
        
        # 기본 검증
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
        status = "PASS" if score >= 80 else "FAIL"
        
        result = {
            "file": target_path,
            "score": score,
            "status": status,
            "issues": issues,
            "summary": f"품질 점수: {score}/100 ({status})",
            "line_diff_percent": round(line_diff, 2),
            "source_lines": source_lines,
            "target_lines": target_lines,
        }
        
        # tasks.md 업데이트 (검토 완료)
        if tasks_path and task_id:
            from agents.task_planner import update_task_status
            update_task_status(tasks_path, task_id, status="completed")
        
        return result
        
    except Exception as e:
        # tasks.md 업데이트 (검토 실패)
        if tasks_path and task_id:
            from agents.task_planner import update_task_status
            update_task_status(tasks_path, task_id, status="not_started")
        
        return {
            "file": target_path,
            "score": 0,
            "status": "ERROR",
            "issues": [str(e)],
            "summary": f"검토 실패: {str(e)}",
        }


def run_reviewer_agent(
    source_path: str,
    target_path: str,
    target_lang: str,
) -> dict:
    """
    Reviewer 에이전트를 실행하여 상세 품질 검토를 수행합니다.
    
    Args:
        source_path: 원본 파일 경로
        target_path: 번역 파일 경로
        target_lang: 타겟 언어 코드
    
    Returns:
        dict: 검토 결과
    """
    # 기본 검토 먼저 수행
    basic_result = review_translation(source_path, target_path, target_lang)
    
    # 점수가 낮으면 에이전트로 상세 검토
    if basic_result["score"] < 90:
        agent = Agent(
            model=load_sonnet(),
            system_prompt=REVIEWER_PROMPT,
            tools=[file_read],
        )
        
        prompt = f"""
        번역 품질을 상세히 검토해주세요.
        
        원본 파일: {source_path}
        번역 파일: {target_path}
        타겟 언어: {target_lang}
        
        기본 검토 결과:
        - 점수: {basic_result['score']}/100
        - 문제점: {basic_result['issues']}
        
        추가로 확인해야 할 사항:
        1. AWS 용어 일관성
        2. 문장 자연스러움
        3. 기술 용어 정확성
        """
        
        response = agent(prompt)
        basic_result["agent_review"] = str(response)
    
    return basic_result


@tool
def review_all_translations(
    source_files: list,
    target_lang: str,
    tasks_path: str = None,
) -> dict:
    """
    모든 번역 파일의 품질을 검토합니다.
    
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
        
        # tasks.md의 검토 태스크 ID (예: "4.1", "4.2", ...)
        task_id = f"4.{i+1}" if tasks_path else None
        
        if os.path.exists(target_path):
            result = review_translation(
                source_path, 
                target_path, 
                target_lang,
                tasks_path=tasks_path,
                task_id=task_id
            )
            results.append(result)
            total_score += result["score"]
            
            if result["status"] == "PASS":
                pass_count += 1
            else:
                fail_count += 1
        else:
            results.append({
                "file": target_path,
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

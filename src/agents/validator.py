# Validator 에이전트 - 구조 검증
# Explore 패턴 참고: 빠른 검증, 명확한 결과

import os
import re
from strands import Agent, tool
from strands_tools import file_read
from model.load import load_haiku
from prompts.system_prompts import VALIDATOR_PROMPT
from tools.file_tools import (
    read_workshop_file,
    compare_line_counts,
)


def create_validator_agent() -> Agent:
    """
    Validator 에이전트 인스턴스를 생성합니다.
    
    Agent는 다음 도구들을 사용할 수 있습니다:
    - file_read: 파일 내용 읽기 (strands 기본 도구)
    
    Returns:
        Agent: Validator 에이전트 인스턴스
    """
    return Agent(
        model=load_haiku(),
        system_prompt=VALIDATOR_PROMPT,
        tools=[file_read],
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
    broken_links = re.findall(r'\[([^\]]*)\]\([^)]*$', content, re.MULTILINE)
    if broken_links:
        errors.append(f"깨진 링크가 있습니다: {len(broken_links)}개")
    
    # 이미지 형식 확인
    broken_images = re.findall(r'!\[([^\]]*)\]\([^)]*$', content, re.MULTILINE)
    if broken_images:
        errors.append(f"깨진 이미지 링크가 있습니다: {len(broken_images)}개")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


@tool
def validate_structure(
    source_files: list,
    target_lang: str,
    tasks_path: str = None,
    task_id: str = None,
) -> dict:
    """
    번역된 파일들의 구조를 검증합니다.
    
    이 도구는 Orchestrator가 호출하며, 내부에서 Validator Agent를 실행합니다.
    Agent는 LLM을 사용하여 번역 파일의 구조적 정확성을 확인합니다.
    
    Args:
        source_files: 원본 파일 목록
        target_lang: 타겟 언어 코드
        tasks_path: tasks.md 파일 경로 (선택)
        task_id: 태스크 ID (선택, tasks.md 업데이트용)
    
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
    # tasks.md 업데이트 (검증 시작)
    if tasks_path and task_id:
        from agents.task_planner import update_task_status
        update_task_status(tasks_path, task_id, status="in_progress")
    
    errors = []
    warnings = []
    translated_count = 0
    total_line_diff = 0
    
    for source_path in source_files:
        target_path = source_path.replace(".en.md", f".{target_lang}.md")
        
        # 파일 존재 확인
        if not os.path.exists(target_path):
            errors.append(f"{target_path}: 번역 파일이 없습니다")
            continue
        
        translated_count += 1
        
        try:
            content = read_workshop_file(target_path)
            
            # Frontmatter 검증
            fm_result = validate_frontmatter(content)
            for err in fm_result["errors"]:
                errors.append(f"{target_path}: {err}")
            for warn in fm_result["warnings"]:
                warnings.append(f"{target_path}: {warn}")
            
            # Markdown 구문 검증
            md_result = validate_markdown_syntax(content)
            for err in md_result["errors"]:
                errors.append(f"{target_path}: {err}")
            for warn in md_result["warnings"]:
                warnings.append(f"{target_path}: {warn}")
            
            # 줄 수 비교
            line_result = compare_line_counts(source_path, target_path)
            total_line_diff += line_result["diff_percent"]
            
            if line_result["diff_percent"] > 20:
                errors.append(f"{target_path}: 줄 수 차이가 큽니다 ({line_result['diff_percent']:.1f}%)")
            elif line_result["diff_percent"] > 10:
                warnings.append(f"{target_path}: 줄 수 차이 {line_result['diff_percent']:.1f}%")
                
        except Exception as e:
            errors.append(f"{target_path}: 검증 실패 - {str(e)}")
    
    # 결과 집계
    total_files = len(source_files)
    coverage = translated_count / total_files * 100 if total_files > 0 else 0
    avg_line_diff = total_line_diff / translated_count if translated_count > 0 else 0
    
    status = "PASS" if len(errors) == 0 and coverage == 100 else "FAIL"
    
    result = {
        "status": status,
        "coverage": f"{translated_count}/{total_files} files ({coverage:.1f}%)",
        "coverage_percent": round(coverage, 2),
        "line_diff_avg": round(avg_line_diff, 2),
        "errors": errors,
        "warnings": warnings,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }
    
    # tasks.md 업데이트 (검증 완료)
    if tasks_path and task_id:
        from agents.task_planner import update_task_status
        update_task_status(tasks_path, task_id, status="completed")
    
    return result


def run_validator_agent(
    source_files: list[str],
    target_lang: str,
) -> dict:
    """
    Validator 에이전트를 실행하여 상세 검증을 수행합니다.
    
    Args:
        source_files: 원본 파일 목록
        target_lang: 타겟 언어 코드
    
    Returns:
        dict: 검증 결과
    """
    # 기본 검증 먼저 수행
    basic_result = validate_structure(source_files, target_lang)
    
    # 에러가 있으면 에이전트로 상세 분석
    if basic_result["error_count"] > 0:
        agent = Agent(
            model=load_haiku(),
            system_prompt=VALIDATOR_PROMPT,
            tools=[file_read],
        )
        
        prompt = f"""
        구조 검증 결과를 분석하고 해결 방안을 제시해주세요.
        
        검증 결과:
        - 상태: {basic_result['status']}
        - 커버리지: {basic_result['coverage']}
        - 오류 수: {basic_result['error_count']}
        - 경고 수: {basic_result['warning_count']}
        
        오류 목록:
        {chr(10).join(basic_result['errors'][:10])}
        
        해결 방안을 제시해주세요.
        """
        
        response = agent(prompt)
        basic_result["agent_analysis"] = str(response)
    
    return basic_result

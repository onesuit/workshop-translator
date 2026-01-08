# Analyzer 에이전트 - Workshop 구조 분석
# Explore 패턴 참고: 빠른 탐색, 병렬 실행

import os
from strands import Agent, tool
from strands_tools import file_read
from model.load import load_haiku
from prompts.system_prompts import ANALYZER_PROMPT
from tools.file_tools import (
    list_workshop_files,
    read_contentspec,
    get_directory_structure,
    get_supported_languages,
)


@tool
def analyze_workshop(workshop_path: str) -> dict:
    """
    Workshop 구조를 분석하고 번역 대상 파일 목록을 반환합니다.
    
    Args:
        workshop_path: Workshop 디렉토리 경로
    
    Returns:
        dict: 분석 결과
            - workshop_path: Workshop 경로
            - supported_languages: 지원 언어 목록
            - files: 번역 대상 파일 목록
            - file_count: 파일 수
            - structure: 디렉토리 구조
    """
    # 경로 정규화
    workshop_path = os.path.expanduser(workshop_path)
    workshop_path = os.path.abspath(workshop_path)
    
    # 경로 존재 확인
    if not os.path.exists(workshop_path):
        return {
            "error": f"경로가 존재하지 않습니다: {workshop_path}",
            "workshop_path": workshop_path,
            "files": [],
            "file_count": 0,
        }
    
    # 번역 대상 파일 목록
    files = list_workshop_files(workshop_path)
    
    # 지원 언어 확인
    supported_languages = get_supported_languages(workshop_path)
    
    # contentspec 읽기
    contentspec = read_contentspec(workshop_path)
    
    # 디렉토리 구조
    content_path = os.path.join(workshop_path, "content")
    if os.path.exists(content_path):
        structure = get_directory_structure(content_path)
    else:
        structure = get_directory_structure(workshop_path)
    
    return {
        "workshop_path": workshop_path,
        "supported_languages": supported_languages,
        "contentspec": contentspec,
        "files": files,
        "file_count": len(files),
        "structure": structure,
    }


def run_analyzer_agent(workshop_path: str) -> dict:
    """
    Analyzer 에이전트를 실행합니다.
    더 복잡한 분석이 필요할 때 사용합니다.
    
    Args:
        workshop_path: Workshop 디렉토리 경로
    
    Returns:
        dict: 분석 결과
    """
    # 간단한 분석은 도구로 직접 처리
    result = analyze_workshop(workshop_path)
    
    # 에러가 없으면 바로 반환
    if "error" not in result:
        return result
    
    # 에러가 있으면 에이전트로 상세 분석
    agent = Agent(
        model=load_haiku(),
        system_prompt=ANALYZER_PROMPT,
        tools=[file_read],
    )
    
    response = agent(f"Workshop 경로를 분석해주세요: {workshop_path}")
    
    return {
        "workshop_path": workshop_path,
        "agent_response": str(response),
        "files": [],
        "file_count": 0,
    }

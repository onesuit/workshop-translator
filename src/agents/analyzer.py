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
    detect_source_language,
    SUPPORTED_LANG_CODES,
)


@tool
def analyze_workshop(workshop_path: str, source_lang: str = None) -> dict:
    """
    Workshop 구조를 분석하고 번역 대상 파일 목록을 반환합니다.
    소스 언어를 자동 감지합니다 (.en.md 우선, 없으면 다른 언어 파일 탐색).
    
    Args:
        workshop_path: Workshop 디렉토리 경로
        source_lang: 소스 언어 코드 (None이면 자동 감지)
    
    Returns:
        dict: 분석 결과
            - workshop_path: Workshop 경로
            - source_lang: 소스 언어 코드
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
            "source_lang": None,
            "files": [],
            "file_count": 0,
        }
    
    # 소스 언어 감지 및 파일 목록 가져오기
    detected_lang, files = list_workshop_files(workshop_path, source_lang)
    
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
    
    # 소스 언어 메시지
    if detected_lang == "none":
        lang_message = "번역 대상 파일을 찾을 수 없습니다."
    elif detected_lang == "unknown":
        lang_message = "언어 코드 없는 .md 파일을 발견했습니다. 소스 언어를 지정해주세요."
    elif detected_lang != "en":
        lang_message = f".en.md 파일이 없어 .{detected_lang}.md 파일을 소스로 사용합니다."
    else:
        lang_message = None
    
    return {
        "workshop_path": workshop_path,
        "source_lang": detected_lang,
        "source_lang_message": lang_message,
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

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
    read_workshop_file,
)


def create_analyzer_agent() -> Agent:
    """
    Analyzer 에이전트 인스턴스를 생성합니다.
    
    Agent는 다음 도구들을 사용할 수 있습니다:
    - file_read: 파일 내용 읽기 (strands 기본 도구)
    
    Returns:
        Agent: Analyzer 에이전트 인스턴스
    """
    return Agent(
        model=load_haiku(),
        system_prompt=ANALYZER_PROMPT,
        tools=[file_read],
    )


@tool
def analyze_workshop(workshop_path: str, source_lang: str = None) -> dict:
    """
    Workshop 구조를 분석하고 번역 대상 파일 목록을 반환합니다.
    
    이 도구는 Orchestrator가 호출하며, 내부에서 Analyzer Agent를 실행합니다.
    Agent는 LLM을 사용하여 Workshop 구조를 분석하고 필요한 정보를 수집합니다.
    
    Args:
        workshop_path: Workshop 디렉토리 경로
        source_lang: 소스 언어 코드 (None이면 자동 감지)
    
    Returns:
        dict: 분석 결과
            - workshop_path: Workshop 경로
            - source_lang: 소스 언어 코드
            - source_lang_message: 소스 언어 관련 메시지
            - supported_languages: 지원 언어 목록
            - contentspec: contentspec.yaml 내용
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
    
    # Agent 생성 및 실행
    agent = create_analyzer_agent()
    
    # Agent에게 분석 요청
    prompt = f"""
Workshop 경로를 분석해주세요: {workshop_path}

다음 정보를 수집하세요:
1. 소스 언어 자동 감지 (.en.md 우선, 없으면 다른 언어 파일 탐색)
2. contentspec.yaml 확인
3. 번역 대상 파일 목록
4. 디렉토리 구조

반드시 ANALYZER_PROMPT에 명시된 XML 형식으로 결과를 반환하세요.
"""
    
    try:
        response = agent(prompt)
        
        # Agent 응답을 파싱하여 구조화된 결과 생성
        # 실제로는 헬퍼 함수를 사용하여 정확한 데이터 수집
        detected_lang, files = list_workshop_files(workshop_path, source_lang)
        supported_languages = get_supported_languages(workshop_path)
        contentspec = read_contentspec(workshop_path)
        
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
            "agent_response": str(response),  # Agent의 원본 응답 포함
        }
        
    except Exception as e:
        return {
            "error": f"분석 실패: {str(e)}",
            "workshop_path": workshop_path,
            "source_lang": None,
            "files": [],
            "file_count": 0,
        }

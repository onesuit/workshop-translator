# 서브에이전트 베이스 클래스 및 유틸리티
import os
from strands import Agent
from strands_tools import file_read, file_write
from typing import Optional, Callable
from model.load import load_model_by_type


def create_sub_agent(
    model_type: str,
    system_prompt: str,
    tools: Optional[list] = None,
    callback_handler: Optional[Callable] = None
) -> Agent:
    """
    서브에이전트를 생성합니다.
    
    Args:
        model_type: 모델 타입 ("opus", "sonnet", "haiku")
        system_prompt: 시스템 프롬프트
        tools: 사용할 도구 목록 (기본: file_read, file_write)
        callback_handler: 콜백 핸들러 (선택)
    
    Returns:
        Agent: 생성된 에이전트
    """
    if tools is None:
        tools = [file_read, file_write]
    
    agent_kwargs = {
        "model": load_model_by_type(model_type),
        "system_prompt": system_prompt,
        "tools": tools,
    }
    
    if callback_handler:
        agent_kwargs["callback_handler"] = callback_handler
    
    return Agent(**agent_kwargs)


def parse_xml_tag(text: str, tag: str) -> str:
    """
    XML 태그 내용을 추출합니다.
    
    Args:
        text: 전체 텍스트
        tag: 추출할 태그명
    
    Returns:
        str: 태그 내용 (없으면 빈 문자열)
    """
    import re
    pattern = rf"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


def parse_file_list(text: str) -> list[str]:
    """
    파일 목록을 파싱합니다.
    
    Args:
        text: 파일 목록 텍스트 (줄바꿈 또는 - 구분)
    
    Returns:
        list[str]: 파일 경로 목록
    """
    files = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("- "):
            line = line[2:]
        if line and line.endswith(".md"):
            files.append(line)
    return files

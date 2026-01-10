# Translator Worker - Stateless 번역 워커
# 결과만 반환, tasks.md 직접 수정 안 함

import os
from strands import Agent
from strands_tools import file_read, file_write

from model.load import load_sonnet
from prompts.system_prompts import TRANSLATOR_PROMPT
from task_manager.types import TaskResult
from tools.file_tools import read_workshop_file, write_translated_file


def translate_single_file(
    source_path: str,
    target_lang: str,
    source_lang: str = "en"
) -> TaskResult:
    """
    단일 파일 번역 (Stateless Worker)
    
    Stateless 원칙:
    - tasks.md 직접 수정 안 함
    - 결과만 TaskResult로 반환
    - Orchestrator가 결과를 받아 상태 업데이트
    
    Args:
        source_path: 원본 파일 경로
        target_lang: 타겟 언어 코드
        source_lang: 소스 언어 코드
    
    Returns:
        TaskResult: 번역 결과 (성공/실패, 출력 경로, 메타데이터)
    """
    try:
        # 원본 파일 읽기
        source_content = read_workshop_file(source_path)
        
        if not source_content:
            return TaskResult(
                task_id="",  # Orchestrator가 채움
                success=False,
                error=f"원본 파일을 읽을 수 없습니다: {source_path}"
            )
        
        # 언어 이름 매핑
        lang_names = {
            "ko": "한국어 (Korean)",
            "ja": "일본어 (Japanese)",
            "zh": "중국어 간체 (Simplified Chinese)",
            "es": "스페인어 (Spanish)",
            "pt": "포르투갈어 (Portuguese)",
            "fr": "프랑스어 (French)",
            "de": "독일어 (German)",
        }
        target_lang_name = lang_names.get(target_lang, target_lang)
        source_lang_name = lang_names.get(source_lang, source_lang)
        
        # Translator Agent 생성 (Stateless)
        agent = Agent(
            model=load_sonnet(),
            system_prompt=TRANSLATOR_PROMPT,
            tools=[file_read, file_write],
        )
        
        # 번역 프롬프트
        prompt = f"""다음 AWS Workshop 콘텐츠를 {source_lang_name}에서 {target_lang_name}로 번역해주세요.

## 원본 파일
- 경로: {source_path}

## 원본 내용
```markdown
{source_content}
```

## 번역 지침
1. Markdown 구조 유지 (헤더, 리스트, 코드 블록 등)
2. AWS 서비스명, 기술 용어는 영어 유지
3. 코드 블록 내용은 번역하지 않음
4. Hugo shortcode 구문 유지 ({{{{< >}}}}, {{{{%  %}}}})
5. 자연스러운 {target_lang_name} 표현 사용

번역된 전체 내용만 출력해주세요. 설명이나 주석 없이 번역 결과만 반환합니다."""

        # Agent 실행
        response = agent(prompt)
        
        # 응답에서 번역 내용 추출
        translated_content = str(response)
        
        # 코드 블록 마커 제거 (있는 경우)
        if translated_content.startswith("```markdown"):
            translated_content = translated_content[len("```markdown"):].strip()
        if translated_content.startswith("```"):
            translated_content = translated_content[3:].strip()
        if translated_content.endswith("```"):
            translated_content = translated_content[:-3].strip()
        
        # 번역 파일 저장
        target_path = write_translated_file(
            source_path, 
            translated_content, 
            target_lang, 
            source_lang
        )
        
        # 통계 계산
        source_lines = len(source_content.split("\n"))
        target_lines = len(translated_content.split("\n"))
        
        return TaskResult(
            task_id="",  # Orchestrator가 채움
            success=True,
            output_path=target_path,
            metadata={
                "source_path": source_path,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "source_lines": source_lines,
                "target_lines": target_lines,
            }
        )
        
    except Exception as e:
        return TaskResult(
            task_id="",
            success=False,
            error=str(e),
            metadata={"source_path": source_path}
        )

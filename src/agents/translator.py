# Translator 에이전트 - 번역 실행
# Document Writer 패턴 참고: 검증 기반, 정확성 우선

import os
import asyncio
from strands import Agent, tool
from strands_tools import file_read, file_write
from model.load import load_sonnet
from prompts.system_prompts import TRANSLATOR_PROMPT
from tools.file_tools import (
    read_workshop_file,
    write_translated_file,
)


@tool
def translate_file(
    source_path: str,
    target_lang: str,
) -> dict:
    """
    단일 파일을 번역합니다.
    
    Args:
        source_path: 원본 파일 경로 (.en.md)
        target_lang: 타겟 언어 코드 (ko, ja, zh 등)
    
    Returns:
        dict: 번역 결과
            - source_path: 원본 파일 경로
            - target_path: 번역 파일 경로
            - success: 성공 여부
            - error: 에러 메시지 (실패 시)
    """
    try:
        # 원본 파일 읽기
        source_content = read_workshop_file(source_path)
        
        # 에이전트로 번역
        agent = Agent(
            model=load_sonnet(),
            system_prompt=TRANSLATOR_PROMPT,
            tools=[],  # 번역에는 도구 불필요
        )
        
        # 언어 이름 매핑
        lang_names = {
            "ko": "한국어",
            "ja": "日本語",
            "zh": "中文",
            "es": "Español",
            "fr": "Français",
            "de": "Deutsch",
            "pt": "Português",
        }
        target_lang_name = lang_names.get(target_lang, target_lang)
        
        prompt = f"""
다음 Markdown 파일을 {target_lang_name}({target_lang})로 번역해주세요.

## 번역 규칙
1. AWS 서비스명은 영어 유지 (Amazon SES, AWS Lambda 등)
2. Frontmatter의 title만 번역
3. 코드 블록 내용은 유지, 주석만 번역
4. 링크 URL은 유지, 텍스트만 번역
5. Markdown 구조 정확히 유지

## 원본 내용
```markdown
{source_content}
```

번역된 전체 Markdown 내용만 반환해주세요. 설명이나 추가 텍스트 없이 번역 결과만 출력하세요.
"""
        
        response = agent(prompt)
        translated_content = str(response)
        
        # 코드 블록 마커 제거 (에이전트가 추가했을 경우)
        if translated_content.startswith("```markdown"):
            translated_content = translated_content[11:]
        if translated_content.startswith("```"):
            translated_content = translated_content[3:]
        if translated_content.endswith("```"):
            translated_content = translated_content[:-3]
        translated_content = translated_content.strip()
        
        # 번역 파일 저장
        target_path = write_translated_file(source_path, translated_content, target_lang)
        
        return {
            "source_path": source_path,
            "target_path": target_path,
            "success": True,
            "source_lines": len(source_content.split("\n")),
            "target_lines": len(translated_content.split("\n")),
        }
        
    except Exception as e:
        return {
            "source_path": source_path,
            "target_path": None,
            "success": False,
            "error": str(e),
        }


async def translate_file_async(
    source_path: str,
    target_lang: str,
) -> dict:
    """
    단일 파일을 비동기로 번역합니다.
    
    Args:
        source_path: 원본 파일 경로
        target_lang: 타겟 언어 코드
    
    Returns:
        dict: 번역 결과
    """
    # 동기 함수를 비동기로 실행
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: translate_file(source_path, target_lang)
    )


@tool
def translate_files_parallel(
    files: list,
    target_lang: str,
    max_concurrent: int = 5,
) -> dict:
    """
    여러 파일을 병렬로 번역합니다.
    
    Args:
        files: 번역 대상 파일 목록
        target_lang: 타겟 언어 코드
        max_concurrent: 최대 동시 실행 수 (기본: 5)
    
    Returns:
        dict: 번역 결과
            - total: 전체 파일 수
            - success: 성공 파일 수
            - failed: 실패 파일 수
            - results: 개별 결과 목록
    """
    results = []
    success_count = 0
    failed_count = 0
    
    # 동기 방식으로 순차 처리 (안정성 우선)
    # TODO: asyncio로 병렬 처리 구현
    for file_path in files:
        result = translate_file(file_path, target_lang)
        results.append(result)
        
        if result["success"]:
            success_count += 1
        else:
            failed_count += 1
    
    return {
        "total": len(files),
        "success": success_count,
        "failed": failed_count,
        "results": results,
    }


async def translate_files_parallel_async(
    files: list[str],
    target_lang: str,
    max_concurrent: int = 5,
) -> dict:
    """
    여러 파일을 비동기 병렬로 번역합니다.
    
    Args:
        files: 번역 대상 파일 목록
        target_lang: 타겟 언어 코드
        max_concurrent: 최대 동시 실행 수
    
    Returns:
        dict: 번역 결과
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def translate_with_semaphore(file_path: str) -> dict:
        async with semaphore:
            return await translate_file_async(file_path, target_lang)
    
    # 모든 파일 병렬 번역
    tasks = [translate_with_semaphore(f) for f in files]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 결과 집계
    success_count = 0
    failed_count = 0
    processed_results = []
    
    for result in results:
        if isinstance(result, Exception):
            processed_results.append({
                "success": False,
                "error": str(result),
            })
            failed_count += 1
        elif result.get("success"):
            processed_results.append(result)
            success_count += 1
        else:
            processed_results.append(result)
            failed_count += 1
    
    return {
        "total": len(files),
        "success": success_count,
        "failed": failed_count,
        "results": processed_results,
    }

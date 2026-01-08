# Translator 에이전트 - 번역 실행
# Document Writer 패턴 참고: 검증 기반, 정확성 우선

import os
import threading
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
    source_lang: str = "en",
) -> dict:
    """
    단일 파일을 번역합니다.
    
    Args:
        source_path: 원본 파일 경로 (.{source_lang}.md)
        target_lang: 타겟 언어 코드 (ko, ja, zh 등)
        source_lang: 소스 언어 코드 (기본: en)
    
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
        
        prompt = f"""
다음 Markdown 파일을 {source_lang_name}({source_lang})에서 {target_lang_name}({target_lang})로 번역해주세요.

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
        target_path = write_translated_file(source_path, translated_content, target_lang, source_lang)
        
        return {
            "source_path": source_path,
            "target_path": target_path,
            "source_lang": source_lang,
            "target_lang": target_lang,
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


@tool
def translate_files_parallel(
    files: list,
    target_lang: str,
    tasks_path: str,
    source_lang: str = "en",
    max_concurrent: int = 5,
) -> dict:
    """
    여러 파일을 병렬로 번역합니다.
    
    Args:
        files: 번역 대상 파일 목록 (최대 10개 권장)
        target_lang: 타겟 언어 코드 (ko, ja, zh 등)
        tasks_path: tasks.md 파일 경로
        source_lang: 소스 언어 코드 (기본: en)
        max_concurrent: 최대 동시 실행 수 (기본: 5)
    
    Returns:
        dict: 번역 시작 결과
            - status: "started"
            - total: 전체 파일 수
            - tasks: 시작된 태스크 정보 목록
            - message: 상태 메시지
    """
    # 순환 import 방지를 위해 함수 내부에서 import
    from main import app
    from agents.task_planner import update_task_status
    
    # 세마포어로 동시 실행 수 제어
    semaphore = threading.Semaphore(max_concurrent)
    started_tasks = []
    
    for i, file_path in enumerate(files):
        # tasks.md의 태스크 ID 생성 (예: "2.1", "2.2", ...)
        task_id = f"2.{i+1}"
        
        # AgentCore 백그라운드 태스크 추적 시작
        internal_task_id = app.add_async_task("translate", {
            "file": file_path,
            "task_id": task_id,
            "target_lang": target_lang
        })
        
        def translate_worker(path, tid, itid, tlang, slang, tpath):
            """백그라운드 번역 작업"""
            with semaphore:  # 최대 max_concurrent개만 동시 실행
                try:
                    # 번역 실행
                    result = translate_file(path, tlang, slang)
                    
                    # 성공 시 tasks.md 업데이트
                    if result["success"]:
                        update_task_status(tpath, tid, completed=True)
                    
                except Exception as e:
                    print(f"번역 실패 ({path}): {e}")
                
                finally:
                    # AgentCore 태스크 완료 표시
                    app.complete_async_task(itid)
        
        # 백그라운드 스레드 시작
        threading.Thread(
            target=translate_worker,
            args=(file_path, task_id, internal_task_id, target_lang, source_lang, tasks_path),
            daemon=True
        ).start()
        
        started_tasks.append({
            "file": file_path,
            "task_id": task_id,
            "internal_task_id": internal_task_id
        })
    
    return {
        "status": "started",
        "total": len(files),
        "max_concurrent": max_concurrent,
        "tasks": started_tasks,
        "message": f"{len(files)}개 파일 번역 시작 (최대 {max_concurrent}개 동시 실행)"
    }


@tool
def check_background_tasks() -> dict:
    """
    백그라운드 번역 작업 상태를 확인합니다.
    
    Returns:
        dict: 작업 상태 정보
            - status: "busy" 또는 "idle"
            - running_tasks: 실행 중인 태스크 수
            - tasks: 태스크 상세 정보 목록
    """
    # 순환 import 방지를 위해 함수 내부에서 import
    from main import app
    
    task_info = app.get_async_task_info()
    tasks = task_info.get("tasks", [])
    
    return {
        "status": "busy" if tasks else "idle",
        "running_tasks": len(tasks),
        "tasks": tasks,
        "message": f"실행 중: {len(tasks)}개" if tasks else "모든 작업 완료"
    }


# =============================================================================
# 아래 함수들은 참고용으로 주석 처리 (나중에 필요할 수 있음)
# =============================================================================

# async def translate_file_async(
#     source_path: str,
#     target_lang: str,
# ) -> dict:
#     """
#     단일 파일을 비동기로 번역합니다.
#     
#     Args:
#         source_path: 원본 파일 경로
#         target_lang: 타겟 언어 코드
#     
#     Returns:
#         dict: 번역 결과
#     """
#     # 동기 함수를 비동기로 실행
#     loop = asyncio.get_event_loop()
#     return await loop.run_in_executor(
#         None,
#         lambda: translate_file(source_path, target_lang)
#     )


# async def translate_files_parallel_async(
#     files: list[str],
#     target_lang: str,
#     max_concurrent: int = 5,
# ) -> dict:
#     """
#     여러 파일을 비동기 병렬로 번역합니다.
#     
#     Args:
#         files: 번역 대상 파일 목록
#         target_lang: 타겟 언어 코드
#         max_concurrent: 최대 동시 실행 수
#     
#     Returns:
#         dict: 번역 결과
#     """
#     semaphore = asyncio.Semaphore(max_concurrent)
#     
#     async def translate_with_semaphore(file_path: str) -> dict:
#         async with semaphore:
#             return await translate_file_async(file_path, target_lang)
#     
#     # 모든 파일 병렬 번역
#     tasks = [translate_with_semaphore(f) for f in files]
#     results = await asyncio.gather(*tasks, return_exceptions=True)
#     
#     # 결과 집계
#     success_count = 0
#     failed_count = 0
#     processed_results = []
#     
#     for result in results:
#         if isinstance(result, Exception):
#             processed_results.append({
#                 "success": False,
#                 "error": str(result),
#             })
#             failed_count += 1
#         elif result.get("success"):
#             processed_results.append(result)
#             success_count += 1
#         else:
#             processed_results.append(result)
#             failed_count += 1
#     
#     return {
#         "total": len(files),
#         "success": success_count,
#         "failed": failed_count,
#         "results": processed_results,
#     }

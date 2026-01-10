# Orchestrator 도구 - 중앙 집중식 워크플로우 관리

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional
from strands import tool

from task_manager.manager import get_task_manager
from task_manager.types import TaskType, TaskResult
from agents.workers.translator_worker import translate_single_file
from agents.workers.reviewer_worker import review_single_file
from agents.workers.validator_worker import validate_single_file


@tool
def initialize_workflow(
    workshop_path: str,
    target_lang: str,
    files: list
) -> dict:
    """
    워크플로우 초기화 및 tasks.md 생성
    
    이 도구는 번역 워크플로우를 시작하기 전에 호출해야 합니다.
    TaskManager를 초기화하고 tasks.md 파일을 생성합니다.
    
    Args:
        workshop_path: Workshop 디렉토리 경로
        target_lang: 타겟 언어 코드 (ko, ja, zh 등)
        files: 번역 대상 파일 목록
    
    Returns:
        dict: 초기화 결과
            - tasks_path: 생성된 tasks.md 경로
            - total_tasks: 총 태스크 수
            - file_count: 파일 수
    """
    manager = get_task_manager()
    tasks_path = manager.initialize(workshop_path, target_lang, files)
    progress = manager.get_progress()
    
    return {
        "tasks_path": tasks_path,
        "total_tasks": progress.total,
        "file_count": len(files),
        "message": f"워크플로우 초기화 완료. {len(files)}개 파일, {progress.total}개 태스크 생성됨."
    }


@tool
def run_translation_phase(max_concurrent: int = 5) -> dict:
    """
    번역 단계 실행 (Orchestrator 전용)
    
    워크플로우:
    1. TaskManager에서 실행 가능한 번역 태스크 조회
    2. 병렬로 Stateless 워커 실행
    3. 결과 수집 후 TaskManager에 보고 (중앙 상태 업데이트)
    4. tasks.md 자동 동기화
    
    Args:
        max_concurrent: 최대 동시 실행 수 (기본: 5)
    
    Returns:
        dict: 실행 결과 요약
    """
    manager = get_task_manager()
    target_lang = manager.target_lang
    
    if not target_lang:
        return {"error": "워크플로우가 초기화되지 않았습니다. initialize_workflow를 먼저 호출하세요."}
    
    # 실행 가능한 번역 태스크 조회
    ready_tasks = manager.get_ready_tasks(TaskType.TRANSLATE, limit=max_concurrent)
    
    if not ready_tasks:
        progress = manager.get_phase_progress(TaskType.TRANSLATE)
        return {
            "message": "실행 가능한 번역 태스크가 없습니다.",
            "completed": progress.completed,
            "total": progress.total,
            "progress_percent": progress.progress_percent,
        }
    
    results = []
    
    # 병렬 실행
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = {}
        
        for task in ready_tasks:
            # 진행 중으로 표시
            manager.mark_in_progress(task.id)
            
            # 워커 실행 (Stateless)
            future = executor.submit(
                translate_single_file,
                task.file_path,
                target_lang
            )
            futures[future] = task.id
        
        # 결과 수집
        for future in as_completed(futures):
            task_id = futures[future]
            result = future.result()
            result.task_id = task_id
            
            # Orchestrator가 중앙에서 상태 업데이트
            manager.complete_task(result)
            results.append(result)
    
    # 진행 상황 반환
    progress = manager.get_phase_progress(TaskType.TRANSLATE)
    
    return {
        "executed": len(results),
        "succeeded": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "phase_progress": progress.to_dict(),
        "results": [r.to_dict() for r in results],
    }


@tool
def run_review_phase(max_concurrent: int = 5) -> dict:
    """
    검토 단계 실행 (Orchestrator 전용)
    
    번역이 완료된 파일만 자동으로 선택하여 검토합니다.
    의존성(번역 완료)이 충족된 태스크만 실행됩니다.
    
    Args:
        max_concurrent: 최대 동시 실행 수 (기본: 5)
    
    Returns:
        dict: 실행 결과 요약
    """
    manager = get_task_manager()
    target_lang = manager.target_lang
    
    if not target_lang:
        return {"error": "워크플로우가 초기화되지 않았습니다."}
    
    # 실행 가능한 검토 태스크 조회 (번역 완료된 것만)
    ready_tasks = manager.get_ready_tasks(TaskType.REVIEW, limit=max_concurrent)
    
    if not ready_tasks:
        progress = manager.get_phase_progress(TaskType.REVIEW)
        return {
            "message": "실행 가능한 검토 태스크가 없습니다. 번역이 완료되었는지 확인하세요.",
            "completed": progress.completed,
            "total": progress.total,
            "progress_percent": progress.progress_percent,
        }
    
    results = []
    source_lang = "en"
    
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = {}
        
        for task in ready_tasks:
            manager.mark_in_progress(task.id)
            
            # 타겟 파일 경로 계산
            target_path = task.file_path.replace(f".{source_lang}.md", f".{target_lang}.md")
            
            future = executor.submit(
                review_single_file,
                task.file_path,  # source_path
                target_path,
                target_lang,
                source_lang
            )
            futures[future] = task.id
        
        for future in as_completed(futures):
            task_id = futures[future]
            result = future.result()
            result.task_id = task_id
            manager.complete_task(result)
            results.append(result)
    
    progress = manager.get_phase_progress(TaskType.REVIEW)
    
    return {
        "executed": len(results),
        "succeeded": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "phase_progress": progress.to_dict(),
        "results": [r.to_dict() for r in results],
    }


@tool
def run_validate_phase(max_concurrent: int = 5) -> dict:
    """
    검증 단계 실행 (Orchestrator 전용)
    
    번역과 검토가 모두 완료된 파일만 자동으로 선택하여 검증합니다.
    
    Args:
        max_concurrent: 최대 동시 실행 수 (기본: 5)
    
    Returns:
        dict: 실행 결과 요약
    """
    manager = get_task_manager()
    target_lang = manager.target_lang
    
    if not target_lang:
        return {"error": "워크플로우가 초기화되지 않았습니다."}
    
    # 실행 가능한 검증 태스크 조회 (번역+검토 완료된 것만)
    ready_tasks = manager.get_ready_tasks(TaskType.VALIDATE, limit=max_concurrent)
    
    if not ready_tasks:
        progress = manager.get_phase_progress(TaskType.VALIDATE)
        return {
            "message": "실행 가능한 검증 태스크가 없습니다. 번역과 검토가 완료되었는지 확인하세요.",
            "completed": progress.completed,
            "total": progress.total,
            "progress_percent": progress.progress_percent,
        }
    
    results = []
    source_lang = "en"
    
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = {}
        
        for task in ready_tasks:
            manager.mark_in_progress(task.id)
            
            target_path = task.file_path.replace(f".{source_lang}.md", f".{target_lang}.md")
            
            future = executor.submit(
                validate_single_file,
                task.file_path,
                target_path,
                target_lang,
                source_lang
            )
            futures[future] = task.id
        
        for future in as_completed(futures):
            task_id = futures[future]
            result = future.result()
            result.task_id = task_id
            manager.complete_task(result)
            results.append(result)
    
    progress = manager.get_phase_progress(TaskType.VALIDATE)
    
    return {
        "executed": len(results),
        "succeeded": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "phase_progress": progress.to_dict(),
        "results": [r.to_dict() for r in results],
    }


@tool
def get_workflow_status() -> dict:
    """
    전체 워크플로우 상태 조회
    
    현재 워크플로우의 진행 상황을 반환합니다.
    각 단계(번역, 검토, 검증)별 진행률을 확인할 수 있습니다.
    
    Returns:
        dict: 워크플로우 상태
    """
    manager = get_task_manager()
    
    if not manager.tasks_path:
        return {"error": "워크플로우가 초기화되지 않았습니다."}
    
    overall = manager.get_progress()
    translate = manager.get_phase_progress(TaskType.TRANSLATE)
    review = manager.get_phase_progress(TaskType.REVIEW)
    validate = manager.get_phase_progress(TaskType.VALIDATE)
    
    return {
        "tasks_path": manager.tasks_path,
        "target_lang": manager.target_lang,
        "overall": overall.to_dict(),
        "phases": {
            "translate": translate.to_dict(),
            "review": review.to_dict(),
            "validate": validate.to_dict(),
        },
        "is_complete": overall.is_complete,
        "has_failures": overall.has_failures,
    }


@tool
def retry_failed_tasks(task_type: str = None, max_retries: int = 3) -> dict:
    """
    실패한 태스크 재시도
    
    실패한 태스크 중 재시도 가능한 것들을 다시 실행합니다.
    
    Args:
        task_type: 재시도할 태스크 유형 ("translate", "review", "validate")
                   None이면 모든 유형의 실패 태스크 재시도
        max_retries: 최대 재시도 횟수 (기본: 3)
    
    Returns:
        dict: 재시도 결과
    """
    manager = get_task_manager()
    
    if not manager.tasks_path:
        return {"error": "워크플로우가 초기화되지 않았습니다."}
    
    # 태스크 유형 변환
    type_filter = None
    if task_type:
        type_map = {
            "translate": TaskType.TRANSLATE,
            "review": TaskType.REVIEW,
            "validate": TaskType.VALIDATE,
        }
        type_filter = type_map.get(task_type.lower())
    
    # 실패한 태스크 조회
    failed_tasks = manager.get_failed_tasks(type_filter)
    
    if not failed_tasks:
        return {"message": "재시도할 실패 태스크가 없습니다."}
    
    # 재시도 가능한 태스크만 리셋
    reset_count = 0
    for task in failed_tasks:
        if task.retry_count < max_retries:
            manager.reset_for_retry(task.id)
            reset_count += 1
    
    return {
        "message": f"{reset_count}개 태스크가 재시도를 위해 리셋되었습니다.",
        "reset_count": reset_count,
        "total_failed": len(failed_tasks),
        "hint": "run_translation_phase, run_review_phase, run_validate_phase를 다시 호출하세요.",
    }


@tool
def check_phase_completion(phase: str) -> dict:
    """
    특정 단계의 완료 여부 확인
    
    Args:
        phase: 확인할 단계 ("translate", "review", "validate")
    
    Returns:
        dict: 완료 상태 및 다음 단계 안내
    """
    manager = get_task_manager()
    
    if not manager.tasks_path:
        return {"error": "워크플로우가 초기화되지 않았습니다."}
    
    type_map = {
        "translate": TaskType.TRANSLATE,
        "review": TaskType.REVIEW,
        "validate": TaskType.VALIDATE,
    }
    
    task_type = type_map.get(phase.lower())
    if not task_type:
        return {"error": f"알 수 없는 단계: {phase}"}
    
    progress = manager.get_phase_progress(task_type)
    
    next_phase_map = {
        "translate": "review",
        "review": "validate",
        "validate": None,
    }
    next_phase = next_phase_map.get(phase.lower())
    
    result = {
        "phase": phase,
        "is_complete": progress.is_complete,
        "progress": progress.to_dict(),
    }
    
    if progress.is_complete:
        if next_phase:
            result["next_action"] = f"run_{next_phase}_phase를 호출하세요."
        else:
            result["next_action"] = "모든 단계가 완료되었습니다!"
    else:
        if progress.has_failures:
            result["next_action"] = f"retry_failed_tasks('{phase}')로 실패한 태스크를 재시도하거나, run_{phase}_phase를 다시 호출하세요."
        else:
            result["next_action"] = f"run_{phase}_phase를 호출하여 남은 태스크를 처리하세요."
    
    return result

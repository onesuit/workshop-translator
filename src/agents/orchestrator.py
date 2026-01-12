# Orchestrator 도구 - 중앙 집중식 워크플로우 관리

import os
import shutil
import subprocess
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Optional
from strands import tool

from task_manager.manager import get_task_manager
from task_manager.types import TaskType, TaskResult
from agents.workers.translator_worker import translate_single_file
from agents.workers.reviewer_worker import review_single_file
from agents.workers.validator_worker import validate_single_file


# Preview 프로세스 관리를 위한 전역 변수
_preview_process = None
_preview_port = None


def _generate_review_report(manager, results: list) -> str:
    """검토 단계 리포트 생성"""
    progress = manager.get_phase_progress(TaskType.REVIEW)
    translate_progress = manager.get_phase_progress(TaskType.TRANSLATE)
    
    # 결과 분류
    passed = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    # 점수 통계
    scores = []
    for r in results:
        if r.metadata and "score" in r.metadata:
            scores.append(r.metadata["score"])
    
    avg_score = sum(scores) / len(scores) if scores else 0
    
    report = f"""# 📋 검토(Review) 단계 리포트

생성 시간: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📊 요약

| 항목 | 값 |
|------|-----|
| 총 파일 수 | {progress.total} |
| 검토 완료 | {progress.completed} |
| 통과 (PASS) | {len(passed)} |
| 실패 (FAIL) | {len(failed)} |
| 평균 점수 | {avg_score:.1f}/100 |
| 진행률 | {progress.progress_percent:.1f}% |

## ✅ 통과한 파일 (PASS)

"""
    
    if passed:
        for r in passed:
            score = r.metadata.get("score", "-") if r.metadata else "-"
            path = r.metadata.get("target_path", r.output_path or "-") if r.metadata else "-"
            report += f"- [{score}점] `{path}`\n"
    else:
        report += "_통과한 파일이 없습니다._\n"
    
    report += "\n## ❌ 실패한 파일 (FAIL)\n\n"
    
    if failed:
        for r in failed:
            score = r.metadata.get("score", "-") if r.metadata else "-"
            path = r.metadata.get("target_path", "-") if r.metadata else "-"
            issues = r.metadata.get("issues", r.error or "-") if r.metadata else (r.error or "-")
            report += f"### `{path}` ({score}점)\n"
            report += f"- **문제점**: {issues[:200]}{'...' if len(str(issues)) > 200 else ''}\n\n"
    else:
        report += "_실패한 파일이 없습니다._\n"
    
    report += f"""
## 📈 단계별 진행 상황

| 단계 | 완료 | 전체 | 진행률 |
|------|------|------|--------|
| 번역 | {translate_progress.completed} | {translate_progress.total} | {translate_progress.progress_percent:.1f}% |
| 검토 | {progress.completed} | {progress.total} | {progress.progress_percent:.1f}% |

## 🔄 다음 단계

"""
    
    if progress.is_complete:
        report += "검토 단계가 완료되었습니다. `run_validate_phase`를 호출하여 검증 단계를 진행하세요.\n"
    elif failed:
        report += f"{len(failed)}개 파일이 검토에 실패했습니다. `retry_failed_tasks('review')`로 재시도하거나 수동으로 수정하세요.\n"
    else:
        report += "검토가 진행 중입니다. `run_review_phase`를 다시 호출하여 남은 파일을 처리하세요.\n"
    
    return report


def _generate_validate_report(manager, results: list) -> str:
    """검증 단계 리포트 생성"""
    progress = manager.get_phase_progress(TaskType.VALIDATE)
    translate_progress = manager.get_phase_progress(TaskType.TRANSLATE)
    review_progress = manager.get_phase_progress(TaskType.REVIEW)
    overall = manager.get_progress()
    
    # 결과 분류
    passed = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    report = f"""# 📋 검증(Validate) 단계 리포트

생성 시간: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📊 요약

| 항목 | 값 |
|------|-----|
| 총 파일 수 | {progress.total} |
| 검증 완료 | {progress.completed} |
| 통과 (PASS) | {len(passed)} |
| 실패 (FAIL) | {len(failed)} |
| 진행률 | {progress.progress_percent:.1f}% |

## ✅ 검증 통과 파일

"""
    
    if passed:
        for r in passed:
            path = r.metadata.get("target_path", r.output_path or "-") if r.metadata else "-"
            report += f"- `{path}`\n"
    else:
        report += "_검증 통과한 파일이 없습니다._\n"
    
    report += "\n## ❌ 검증 실패 파일\n\n"
    
    if failed:
        for r in failed:
            path = r.metadata.get("target_path", "-") if r.metadata else "-"
            issues = r.metadata.get("issues", r.error or "-") if r.metadata else (r.error or "-")
            report += f"### `{path}`\n"
            report += f"- **문제점**: {issues[:300]}{'...' if len(str(issues)) > 300 else ''}\n\n"
    else:
        report += "_검증 실패한 파일이 없습니다._\n"
    
    report += f"""
## 📈 전체 워크플로우 진행 상황

| 단계 | 완료 | 전체 | 진행률 | 상태 |
|------|------|------|--------|------|
| 번역 | {translate_progress.completed} | {translate_progress.total} | {translate_progress.progress_percent:.1f}% | {'✅' if translate_progress.is_complete else '🔄'} |
| 검토 | {review_progress.completed} | {review_progress.total} | {review_progress.progress_percent:.1f}% | {'✅' if review_progress.is_complete else '🔄'} |
| 검증 | {progress.completed} | {progress.total} | {progress.progress_percent:.1f}% | {'✅' if progress.is_complete else '🔄'} |

**전체 진행률**: {overall.progress_percent:.1f}% ({overall.completed}/{overall.total})

## 🎯 최종 상태

"""
    
    if overall.is_complete and not overall.has_failures:
        report += "🎉 **모든 단계가 성공적으로 완료되었습니다!**\n\n번역된 파일들을 확인하고 배포할 준비가 되었습니다.\n"
    elif overall.is_complete:
        report += f"⚠️ **워크플로우가 완료되었지만 일부 실패가 있습니다.**\n\n실패한 파일들을 수동으로 확인하거나 `retry_failed_tasks`로 재시도하세요.\n"
    else:
        report += "🔄 **워크플로우가 아직 진행 중입니다.**\n\n남은 단계를 계속 진행하세요.\n"
    
    return report


def _save_report(manager, report_content: str, report_name: str) -> str:
    """리포트를 파일로 저장"""
    if not manager.tasks_path:
        return None
    
    # tasks.md와 같은 디렉토리에 저장
    report_dir = os.path.dirname(manager.tasks_path)
    report_path = os.path.join(report_dir, report_name)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    return report_path


@tool
def initialize_workflow(
    workshop_path: str,
    target_lang: str,
    files: list,
    force_reset: bool = False
) -> dict:
    """
    워크플로우 초기화 및 tasks.md 생성/로드
    
    이 도구는 번역 워크플로우를 시작하기 전에 호출해야 합니다.
    TaskManager를 초기화하고 tasks.md 파일을 생성합니다.
    
    기존 tasks.md가 있으면 상태를 로드하여 이어서 작업할 수 있습니다.
    force_reset=True로 설정하면 기존 상태를 무시하고 새로 시작합니다.
    
    Args:
        workshop_path: Workshop 디렉토리 경로
        target_lang: 타겟 언어 코드 (ko, ja, zh 등)
        files: 번역 대상 파일 목록
        force_reset: True면 기존 tasks.md 무시하고 새로 생성 (기본: False)
    
    Returns:
        dict: 초기화 결과
            - tasks_path: 생성된 tasks.md 경로
            - total_tasks: 총 태스크 수
            - file_count: 파일 수
            - resumed: 기존 상태에서 재개 여부
    """
    manager = get_task_manager()
    
    # 기존 tasks.md 존재 여부 확인
    import os
    tasks_path_check = os.path.join(workshop_path, "translation", "tasks.md")
    had_existing = os.path.exists(tasks_path_check) and not force_reset
    
    tasks_path = manager.initialize(workshop_path, target_lang, files, force_reset=force_reset)
    progress = manager.get_progress()
    
    if had_existing and progress.completed > 0:
        message = f"기존 워크플로우 재개. {progress.completed}/{progress.total} 태스크 완료 상태 로드됨."
    else:
        message = f"워크플로우 초기화 완료. {len(files)}개 파일, {progress.total}개 태스크 생성됨."
    
    return {
        "tasks_path": tasks_path,
        "total_tasks": progress.total,
        "file_count": len(files),
        "resumed": had_existing and progress.completed > 0,
        "progress": progress.to_dict(),
        "message": message
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
    
    # 리포트 생성 (단계 완료 또는 결과가 있을 때)
    report_path = None
    if results:
        # 전체 결과를 포함하여 리포트 생성
        all_results = results  # 현재 실행 결과
        report_content = _generate_review_report(manager, all_results)
        report_path = _save_report(manager, report_content, "review_report.md")
    
    return {
        "executed": len(results),
        "succeeded": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "phase_progress": progress.to_dict(),
        "results": [r.to_dict() for r in results],
        "report_path": report_path,
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
    
    # 리포트 생성 (단계 완료 또는 결과가 있을 때)
    report_path = None
    if results:
        report_content = _generate_validate_report(manager, results)
        report_path = _save_report(manager, report_content, "validate_report.md")
    
    return {
        "executed": len(results),
        "succeeded": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "phase_progress": progress.to_dict(),
        "results": [r.to_dict() for r in results],
        "report_path": report_path,
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



# Preview 빌드 파일 경로 (패키지 내부)
def _get_preview_build_path() -> str:
    """preview_build 파일 경로 반환"""
    import sys
    
    # 1. 현재 모듈과 같은 디렉토리에서 찾기 (패키지 설치 시)
    module_dir = os.path.dirname(os.path.abspath(__file__))
    
    # agents/orchestrator.py -> agents/ -> src/ (또는 설치된 패키지 루트)
    # 설치된 패키지에서는 preview_build가 루트에 있음
    package_root = os.path.dirname(os.path.dirname(module_dir))
    candidate = os.path.join(package_root, "preview_build")
    if os.path.exists(candidate):
        return candidate
    
    # 2. 같은 레벨 (agents와 같은 레벨)에서 찾기
    parent_dir = os.path.dirname(module_dir)
    candidate = os.path.join(parent_dir, "preview_build")
    if os.path.exists(candidate):
        return candidate
    
    # 3. sys.path에서 찾기
    for path in sys.path:
        candidate = os.path.join(path, "preview_build")
        if os.path.exists(candidate):
            return candidate
    
    # 4. 개발 환경: WsTranslator 디렉토리에서 찾기
    # src/agents/orchestrator.py -> src/ -> WsTranslator/
    dev_root = os.path.dirname(package_root)
    candidate = os.path.join(dev_root, "preview_build")
    if os.path.exists(candidate):
        return candidate
    
    # 5. 상위 디렉토리 탐색
    current = module_dir
    for _ in range(6):
        candidate = os.path.join(current, "preview_build")
        if os.path.exists(candidate):
            return candidate
        current = os.path.dirname(current)
    
    return None


@tool
def run_preview_phase(port: int = 8080) -> dict:
    """
    로컬 프리뷰 서버 실행 (Orchestrator 전용)
    
    번역된 Workshop을 로컬에서 미리보기 할 수 있습니다.
    preview_build 파일을 workshop 경로에 복사하고 백그라운드로 실행합니다.
    
    프리뷰 서버를 종료하려면 stop_preview를 호출하세요.
    
    Args:
        port: 프리뷰 서버 포트 (기본: 8080)
    
    Returns:
        dict: 프리뷰 서버 정보
            - url: 프리뷰 URL (http://localhost:8080)
            - message: 안내 메시지
    """
    global _preview_process, _preview_port
    
    manager = get_task_manager()
    
    if not manager.tasks_path:
        return {"error": "워크플로우가 초기화되지 않았습니다. initialize_workflow를 먼저 호출하세요."}
    
    # 이미 실행 중인 프로세스가 있으면 종료
    if _preview_process is not None:
        try:
            _preview_process.terminate()
            _preview_process.wait(timeout=5)
        except:
            pass
        _preview_process = None
    
    # Workshop 경로 (사용자가 initialize_workflow에서 지정한 경로)
    workshop_path = manager._workshop_path
    
    if not workshop_path:
        return {"error": "Workshop 경로를 찾을 수 없습니다."}
    
    # preview_build 파일 찾기
    preview_build_src = _get_preview_build_path()
    
    if not preview_build_src:
        return {
            "error": "preview_build 파일을 찾을 수 없습니다.",
            "hint": "WsTranslator 패키지에 preview_build 파일이 포함되어 있는지 확인하세요."
        }
    
    # Workshop 루트 경로에 복사
    preview_build_dst = os.path.join(workshop_path, "preview_build")
    
    try:
        shutil.copy2(preview_build_src, preview_build_dst)
        # 실행 권한 부여
        os.chmod(preview_build_dst, 0o755)
    except Exception as e:
        return {"error": f"preview_build 복사 실패: {e}"}
    
    # 백그라운드로 실행
    try:
        _preview_process = subprocess.Popen(
            [preview_build_dst, "-port", str(port)],
            cwd=workshop_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True  # 독립적인 프로세스 그룹
        )
        _preview_port = port
        
        # 잠시 대기하여 프로세스가 정상 시작되었는지 확인
        import time
        time.sleep(2)
        
        if _preview_process.poll() is not None:
            # 프로세스가 종료됨
            stdout, stderr = _preview_process.communicate()
            return {
                "error": "프리뷰 서버 시작 실패",
                "stderr": stderr.decode("utf-8", errors="ignore")[:500]
            }
        
        return {
            "url": f"http://localhost:{port}",
            "message": f"🚀 프리뷰 서버가 시작되었습니다!\n\n"
                      f"📍 URL: http://localhost:{port}\n"
                      f"📁 Workshop 경로: {workshop_path}\n\n"
                      f"브라우저에서 위 URL을 열어 번역 결과를 확인하세요.\n"
                      f"파일 변경 시 자동으로 새로고침됩니다.\n\n"
                      f"⚠️ 프리뷰를 종료하려면 'stop_preview'를 호출하세요.",
            "workshop_path": workshop_path,
            "pid": _preview_process.pid,
        }
        
    except Exception as e:
        return {"error": f"프리뷰 서버 실행 실패: {e}"}


@tool
def stop_preview() -> dict:
    """
    로컬 프리뷰 서버 종료
    
    run_preview_phase로 시작한 프리뷰 서버를 종료합니다.
    
    Returns:
        dict: 종료 결과
    """
    global _preview_process, _preview_port
    
    if _preview_process is None:
        return {"message": "실행 중인 프리뷰 서버가 없습니다."}
    
    try:
        # 프로세스 그룹 전체 종료
        os.killpg(os.getpgid(_preview_process.pid), signal.SIGTERM)
        _preview_process.wait(timeout=5)
        
        port = _preview_port
        _preview_process = None
        _preview_port = None
        
        return {
            "message": f"✅ 프리뷰 서버가 종료되었습니다. (포트: {port})",
            "stopped": True
        }
    except subprocess.TimeoutExpired:
        # 강제 종료
        os.killpg(os.getpgid(_preview_process.pid), signal.SIGKILL)
        _preview_process = None
        _preview_port = None
        return {"message": "프리뷰 서버가 강제 종료되었습니다.", "stopped": True}
    except Exception as e:
        return {"error": f"프리뷰 서버 종료 실패: {e}"}

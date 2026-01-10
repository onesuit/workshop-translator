# TaskManager - 중앙 집중식 태스크 관리자
# Orchestrator만 상태 파일 수정

import os
import re
import threading
from typing import Dict, List, Optional
from datetime import datetime

from .types import Task, TaskStatus, TaskType, TaskResult, WorkflowProgress


class TaskManager:
    """
    중앙 집중식 태스크 관리자 (싱글톤)
    
    핵심 원칙:
    1. Orchestrator만 이 클래스를 통해 tasks.md 수정
    2. Sub-agent는 TaskResult만 반환, 상태 파일 직접 수정 안 함
    3. 의존성 기반 태스크 실행 관리
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """싱글톤 패턴"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._tasks: Dict[str, Task] = {}
        self._tasks_path: Optional[str] = None
        self._workshop_path: Optional[str] = None
        self._target_lang: Optional[str] = None
        self._files: List[str] = []
        self._initialized = True
    
    def initialize(
        self, 
        workshop_path: str, 
        target_lang: str,
        files: List[str],
        tasks_path: Optional[str] = None,
        force_reset: bool = False
    ) -> str:
        """
        워크플로우 초기화 및 tasks.md 생성/로드
        
        Args:
            workshop_path: Workshop 디렉토리 경로
            target_lang: 타겟 언어 코드
            files: 번역 대상 파일 목록
            tasks_path: tasks.md 경로 (선택)
            force_reset: True면 기존 tasks.md 무시하고 새로 생성
        
        Returns:
            str: 생성된 tasks.md 경로
        """
        self._workshop_path = workshop_path
        self._target_lang = target_lang
        self._files = files
        self._tasks_path = tasks_path or os.path.join(
            workshop_path, "translation", "tasks.md"
        )
        self._tasks.clear()
        
        # 기존 tasks.md가 있으면 상태 로드 시도
        existing_status = {}
        if not force_reset and os.path.exists(self._tasks_path):
            existing_status = self._load_status_from_file()
        
        # 각 파일당 3개 태스크 생성 (translate, review, validate)
        for i, file_path in enumerate(files, start=1):
            base_id = f"2.{i}"
            
            # 번역 태스크
            task_id = f"{base_id}.1"
            self._tasks[task_id] = Task(
                id=task_id,
                type=TaskType.TRANSLATE,
                file_path=file_path,
                depends_on=[],
                status=existing_status.get(task_id, TaskStatus.NOT_STARTED)
            )
            
            # 검토 태스크 (번역 완료 후)
            task_id = f"{base_id}.2"
            self._tasks[task_id] = Task(
                id=task_id,
                type=TaskType.REVIEW,
                file_path=file_path,
                depends_on=[f"{base_id}.1"],
                status=existing_status.get(task_id, TaskStatus.NOT_STARTED)
            )
            
            # 검증 태스크 (번역, 검토 완료 후)
            task_id = f"{base_id}.3"
            self._tasks[task_id] = Task(
                id=task_id,
                type=TaskType.VALIDATE,
                file_path=file_path,
                depends_on=[f"{base_id}.1", f"{base_id}.2"],
                status=existing_status.get(task_id, TaskStatus.NOT_STARTED)
            )
        
        # tasks.md 파일 동기화
        self._sync_to_file()
        
        return self._tasks_path
    
    def _load_status_from_file(self) -> Dict[str, TaskStatus]:
        """
        기존 tasks.md에서 태스크 상태 로드
        
        Returns:
            Dict[str, TaskStatus]: 태스크 ID → 상태 매핑
        """
        status_map = {}
        
        if not self._tasks_path or not os.path.exists(self._tasks_path):
            return status_map
        
        try:
            with open(self._tasks_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 체크박스 패턴 매칭: - [x] 2.1.1 번역 (Translate)
            # 상태: [ ] = NOT_STARTED, [~] = IN_PROGRESS, [x] = COMPLETED, [!] = FAILED
            pattern = r'-\s+\[(.)\]\s+(\d+\.\d+\.\d+)\s+'
            
            for match in re.finditer(pattern, content):
                checkbox = match.group(1)
                task_id = match.group(2)
                
                if checkbox == 'x':
                    status_map[task_id] = TaskStatus.COMPLETED
                elif checkbox == '~':
                    status_map[task_id] = TaskStatus.IN_PROGRESS
                elif checkbox == '!':
                    status_map[task_id] = TaskStatus.FAILED
                else:  # ' ' or anything else
                    status_map[task_id] = TaskStatus.NOT_STARTED
                    
        except Exception as e:
            # 파싱 실패 시 빈 맵 반환 (새로 시작)
            print(f"Warning: tasks.md 파싱 실패, 새로 시작합니다: {e}")
        
        return status_map
    
    def get_ready_tasks(self, task_type: TaskType, limit: int = 5) -> List[Task]:
        """
        실행 가능한 태스크 반환 (의존성 충족된 것만)
        
        Args:
            task_type: 태스크 유형
            limit: 최대 반환 개수 (기본 5개, 병렬 처리용)
        
        Returns:
            List[Task]: 실행 가능한 태스크 목록
        """
        ready = []
        for task in self._tasks.values():
            if task.type != task_type:
                continue
            if task.status != TaskStatus.NOT_STARTED:
                continue
            
            # 의존성 체크
            deps_satisfied = all(
                self._tasks.get(dep_id, Task(id="", type=TaskType.TRANSLATE, file_path="")).status == TaskStatus.COMPLETED
                for dep_id in task.depends_on
            )
            
            if deps_satisfied:
                ready.append(task)
                if len(ready) >= limit:
                    break
        
        return ready
    
    def get_failed_tasks(self, task_type: Optional[TaskType] = None) -> List[Task]:
        """재시도 가능한 실패 태스크 반환"""
        failed = []
        for task in self._tasks.values():
            if task_type and task.type != task_type:
                continue
            if task.status == TaskStatus.FAILED and task.can_retry():
                failed.append(task)
        return failed
    
    def mark_in_progress(self, task_id: str) -> bool:
        """태스크를 진행 중으로 표시"""
        if task_id not in self._tasks:
            return False
        
        task = self._tasks[task_id]
        task.status = TaskStatus.IN_PROGRESS
        task.updated_at = datetime.now()
        self._sync_to_file()
        return True
    
    def complete_task(self, result: TaskResult) -> bool:
        """
        태스크 완료 처리 (Orchestrator가 호출)
        
        Sub-agent의 결과를 받아 중앙에서 상태 업데이트
        """
        task_id = result.task_id
        if task_id not in self._tasks:
            return False
        
        task = self._tasks[task_id]
        task.result = result
        task.updated_at = datetime.now()
        
        if result.success:
            task.status = TaskStatus.COMPLETED
        else:
            task.status = TaskStatus.FAILED
            task.retry_count += 1
        
        self._sync_to_file()
        return True
    
    def reset_for_retry(self, task_id: str) -> bool:
        """실패한 태스크를 재시도를 위해 리셋"""
        if task_id not in self._tasks:
            return False
        
        task = self._tasks[task_id]
        if not task.can_retry():
            return False
        
        task.status = TaskStatus.NOT_STARTED
        task.updated_at = datetime.now()
        self._sync_to_file()
        return True
    
    def get_progress(self) -> WorkflowProgress:
        """전체 워크플로우 진행 상황 반환"""
        total = len(self._tasks)
        completed = sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED)
        in_progress = sum(1 for t in self._tasks.values() if t.status == TaskStatus.IN_PROGRESS)
        failed = sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED)
        not_started = sum(1 for t in self._tasks.values() if t.status == TaskStatus.NOT_STARTED)
        
        return WorkflowProgress(
            total=total,
            completed=completed,
            in_progress=in_progress,
            failed=failed,
            not_started=not_started,
        )
    
    def get_phase_progress(self, task_type: TaskType) -> WorkflowProgress:
        """특정 단계의 진행 상황 반환"""
        tasks = [t for t in self._tasks.values() if t.type == task_type]
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        in_progress = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)
        failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED)
        not_started = sum(1 for t in tasks if t.status == TaskStatus.NOT_STARTED)
        
        return WorkflowProgress(
            total=total,
            completed=completed,
            in_progress=in_progress,
            failed=failed,
            not_started=not_started,
        )
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """특정 태스크 조회"""
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Task]:
        """모든 태스크 반환"""
        return list(self._tasks.values())
    
    @property
    def tasks_path(self) -> Optional[str]:
        return self._tasks_path
    
    @property
    def target_lang(self) -> Optional[str]:
        return self._target_lang
    
    @property
    def workshop_path(self) -> Optional[str]:
        return self._workshop_path
    
    def _sync_to_file(self):
        """메모리 상태를 tasks.md에 동기화 (Orchestrator 전용)"""
        if not self._tasks_path:
            return
        
        # 디렉토리 생성
        os.makedirs(os.path.dirname(self._tasks_path), exist_ok=True)
        
        # tasks.md 내용 생성
        content = self._generate_tasks_md()
        
        with open(self._tasks_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    def _generate_tasks_md(self) -> str:
        """tasks.md 내용 생성"""
        progress = self.get_progress()
        
        lines = [
            "# Implementation Plan",
            "",
            f"**Workshop**: {self._workshop_path}",
            f"**타겟 언어**: {self._target_lang}",
            f"**총 파일 수**: {len(self._files)}개",
            "",
            "---",
            "",
            "## Phase 1: 환경 설정",
            "",
            "- [x] 1.1 타겟 언어 파일 구조 확인",
            "",
            "## Phase 2: 번역 실행",
            "",
        ]
        
        # 파일별 태스크 출력
        for i, file_path in enumerate(self._files, start=1):
            base_id = f"2.{i}"
            
            # 파일명 추출
            rel_path = file_path
            if self._workshop_path and self._workshop_path in file_path:
                rel_path = file_path.replace(self._workshop_path, "").lstrip("/")
            
            # 부모 태스크 상태 계산
            subtasks = [
                self._tasks.get(f"{base_id}.1"),
                self._tasks.get(f"{base_id}.2"),
                self._tasks.get(f"{base_id}.3"),
            ]
            all_completed = all(t and t.status == TaskStatus.COMPLETED for t in subtasks)
            any_in_progress = any(t and t.status == TaskStatus.IN_PROGRESS for t in subtasks)
            
            parent_checkbox = "[x]" if all_completed else "[~]" if any_in_progress else "[ ]"
            lines.append(f"- {parent_checkbox} {base_id} `{rel_path}` 처리")
            
            # 서브태스크
            for task in subtasks:
                if task:
                    checkbox = self._status_to_checkbox(task.status)
                    task_name = self._task_type_to_name(task.type)
                    lines.append(f"  - {checkbox} {task.id} {task_name}")
        
        lines.extend([
            "",
            "## Phase 3: 최종 검증",
            "",
            "- [ ] 3.1 전체 번역 완료 확인",
            "",
            "---",
            "",
            "## 진행 상황",
            "",
            "**체크박스 상태 범례**:",
            "- `[ ]` = 미완료 (Not Started)",
            "- `[~]` = 진행 중 (In Progress)",
            "- `[x]` = 완료 (Completed)",
            "- `[!]` = 실패 (Failed)",
            "",
            f"- 총 태스크: {progress.total}개",
            f"- 완료: {progress.completed}개",
            f"- 진행 중: {progress.in_progress}개",
            f"- 실패: {progress.failed}개",
            f"- 진행률: {progress.progress_percent}%",
        ])
        
        return "\n".join(lines)
    
    def _status_to_checkbox(self, status: TaskStatus) -> str:
        """상태를 체크박스로 변환"""
        mapping = {
            TaskStatus.NOT_STARTED: "[ ]",
            TaskStatus.IN_PROGRESS: "[~]",
            TaskStatus.COMPLETED: "[x]",
            TaskStatus.FAILED: "[!]",
        }
        return mapping.get(status, "[ ]")
    
    def _task_type_to_name(self, task_type: TaskType) -> str:
        """태스크 유형을 이름으로 변환"""
        mapping = {
            TaskType.TRANSLATE: "번역 (Translate)",
            TaskType.REVIEW: "품질 검토 (Review)",
            TaskType.VALIDATE: "구조 검증 (Validate)",
        }
        return mapping.get(task_type, str(task_type))


# 전역 인스턴스 접근 함수
def get_task_manager() -> TaskManager:
    """TaskManager 싱글톤 인스턴스 반환"""
    return TaskManager()

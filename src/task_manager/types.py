# Task Manager 타입 정의

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


class TaskStatus(Enum):
    """태스크 상태"""
    NOT_STARTED = "not_started"   # [ ] 미완료
    IN_PROGRESS = "in_progress"   # [~] 진행 중
    COMPLETED = "completed"       # [x] 완료
    FAILED = "failed"             # [!] 실패


class TaskType(Enum):
    """태스크 유형"""
    TRANSLATE = "translate"   # 번역
    REVIEW = "review"         # 품질 검토
    VALIDATE = "validate"     # 구조 검증


@dataclass
class TaskResult:
    """
    Sub-agent가 반환하는 작업 결과
    
    Sub-agent는 상태 파일을 직접 수정하지 않고
    결과만 반환하여 Orchestrator가 중앙에서 상태를 관리
    """
    task_id: str
    success: bool
    output_path: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None  # 점수, 경고, 통계 등
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "output_path": self.output_path,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class Task:
    """
    개별 태스크 정의
    
    의존성 기반 실행: depends_on에 명시된 태스크가 모두 완료되어야 실행 가능
    """
    id: str                              # 태스크 ID (예: "2.1.1")
    type: TaskType                       # 태스크 유형
    file_path: str                       # 대상 파일 경로
    status: TaskStatus = TaskStatus.NOT_STARTED
    depends_on: List[str] = field(default_factory=list)  # 의존성 태스크 ID들
    result: Optional[TaskResult] = None  # 실행 결과
    retry_count: int = 0                 # 재시도 횟수
    max_retries: int = 3                 # 최대 재시도 횟수
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    def can_retry(self) -> bool:
        """재시도 가능 여부"""
        return self.retry_count < self.max_retries
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "file_path": self.file_path,
            "status": self.status.value,
            "depends_on": self.depends_on,
            "retry_count": self.retry_count,
            "result": self.result.to_dict() if self.result else None,
        }


@dataclass
class WorkflowProgress:
    """워크플로우 진행 상황"""
    total: int
    completed: int
    in_progress: int
    failed: int
    not_started: int
    
    @property
    def progress_percent(self) -> int:
        if self.total == 0:
            return 0
        return int(self.completed / self.total * 100)
    
    @property
    def is_complete(self) -> bool:
        return self.completed == self.total
    
    @property
    def has_failures(self) -> bool:
        return self.failed > 0
    
    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "completed": self.completed,
            "in_progress": self.in_progress,
            "failed": self.failed,
            "not_started": self.not_started,
            "progress_percent": self.progress_percent,
            "is_complete": self.is_complete,
            "has_failures": self.has_failures,
        }

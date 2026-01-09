# TaskPlanner 에이전트 - Tasks 문서 생성
# 체크박스 형식의 실행 가능한 태스크 목록 생성

import os
import re
import threading
from strands import Agent, tool
from strands_tools import file_read, file_write
from model.load import load_sonnet
from prompts.system_prompts import TASK_PLANNER_PROMPT

# tasks.md 파일 접근을 위한 Lock (동시 편집 방지)
_tasks_lock = threading.Lock()


def create_task_planner_agent() -> Agent:
    """
    TaskPlanner 에이전트 인스턴스를 생성합니다.
    
    Agent는 다음 도구들을 사용할 수 있습니다:
    - file_read: 파일 내용 읽기 (strands 기본 도구)
    - file_write: 파일 쓰기 (strands 기본 도구)
    
    Returns:
        Agent: TaskPlanner 에이전트 인스턴스
    """
    return Agent(
        model=load_sonnet(),
        system_prompt=TASK_PLANNER_PROMPT,
        tools=[file_read, file_write],
    )


@tool
def generate_tasks(
    workshop_path: str,
    target_lang: str,
    files: list,
    output_path: str = None
) -> dict:
    """
    Tasks 문서를 생성합니다.
    
    이 도구는 Orchestrator가 호출하며, 내부에서 TaskPlanner Agent를 실행합니다.
    Agent는 LLM을 사용하여 번역 작업을 실행 가능한 태스크로 분해합니다.
    
    각 파일마다 translate/review/validate subtask를 생성하여 병렬 처리와
    진행 상황 추적을 가능하게 합니다.
    
    Args:
        workshop_path: Workshop 디렉토리 경로
        target_lang: 타겟 언어 코드 (ko, ja, zh 등)
        files: 번역 대상 파일 목록
        output_path: 출력 파일 경로 (선택)
    
    Returns:
        dict: 생성 결과
            - content: Tasks 문서 내용
            - output_path: 저장된 파일 경로
            - task_count: 태스크 수
            - file_count: 파일 수
    """
    # Tasks 문서 생성
    lines = [
        "# Implementation Plan",
        "",
        f"**Workshop**: {workshop_path}",
        f"**타겟 언어**: {target_lang}",
        f"**총 파일 수**: {len(files)}개",
        "",
        "---",
        "",
        "## Phase 1: 환경 설정",
        "",
        f"- [ ] 1.1 타겟 언어 ({target_lang}) 파일 구조 확인",
        "  - _Requirements: 2.1, 2.2_",
        "",
        "## Phase 2: 번역 실행",
        "",
    ]
    
    # 파일별 태스크 생성 (translate/review/validate subtask 포함)
    for i, file_path in enumerate(files, start=1):
        # 파일명만 추출
        rel_path = file_path
        if workshop_path in file_path:
            rel_path = file_path.replace(workshop_path, "").lstrip("/")
        
        lines.append(f"- [ ] 2.{i} `{rel_path}` 처리")
        lines.append(f"  - [ ] 2.{i}.1 번역 (Translate)")
        lines.append("    - _Requirements: 1.1, 3.1_")
        lines.append(f"  - [ ] 2.{i}.2 품질 검토 (Review)")
        lines.append("    - _Requirements: 2.{i}.1, 5.1, 5.2_")
        lines.append(f"  - [ ] 2.{i}.3 구조 검증 (Validate)")
        lines.append("    - _Requirements: 2.{i}.1, 6.1, 6.2_")
    
    # 총 subtask 수 계산 (각 파일당 3개: translate, review, validate)
    total_subtasks = len(files) * 3 + 2  # +2 for 1.1 and 3.1
    
    lines.extend([
        "",
        "## Phase 3: 최종 검증",
        "",
        "- [ ] 3.1 전체 번역 완료 확인",
        "  - _Requirements: 2.*, 4.1_",
        "",
        "---",
        "",
        "## 진행 상황",
        "",
        "**체크박스 상태 범례**:",
        "- `[ ]` = 미완료 (Not Started)",
        "- `[~]` = 진행 중 (In Progress)",
        "- `[x]` = 완료 (Completed)",
        "",
        f"- 총 태스크: {total_subtasks}개",
        "- 완료: 0개",
        "- 진행 중: 0개",
        "- 진행률: 0%",
    ])
    
    content = "\n".join(lines)
    
    # 파일 저장
    if output_path is None:
        output_path = os.path.join(workshop_path, "translation", "tasks.md")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return {
        "content": content,
        "output_path": output_path,
        "task_count": total_subtasks,
        "file_count": len(files),
    }


def update_task_status(tasks_path: str, task_id: str, status: str = "completed") -> bool:
    """
    태스크 상태를 업데이트합니다.
    
    체크박스 상태:
    - [ ] = 미완료 (Not Started)
    - [~] = 진행 중 (In Progress)
    - [x] = 완료 (Completed)
    
    Args:
        tasks_path: tasks.md 파일 경로
        task_id: 태스크 ID (예: "2.1")
        status: 상태 ("in_progress", "completed", "not_started")
    
    Returns:
        bool: 업데이트 성공 여부
    """
    # Lock을 사용하여 동시 편집 방지
    with _tasks_lock:
        print(f"[DEBUG] update_task_status 호출: task_id={task_id}, status={status}, path={tasks_path}")
        
        if not os.path.exists(tasks_path):
            print(f"[DEBUG] tasks.md 파일이 존재하지 않음: {tasks_path}")
            return False
        
        with open(tasks_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        print(f"[DEBUG] tasks.md 파일 읽기 성공 (길이: {len(content)})")
        
        # 현재 상태 찾기
        current_patterns = [
            f"- [ ] {task_id}",
            f"- [~] {task_id}",
            f"- [x] {task_id}",
        ]
        
        current_pattern = None
        for pattern in current_patterns:
            if pattern in content:
                current_pattern = pattern
                print(f"[DEBUG] 현재 패턴 발견: {pattern}")
                break
        
        if current_pattern is None:
            print(f"[DEBUG] 태스크 ID를 찾을 수 없음: {task_id}")
            # 가능한 태스크 ID 목록 출력 (디버깅용)
            found_tasks = re.findall(r'- \[.\] (\d+\.\d+(?:\.\d+)?)', content)
            print(f"[DEBUG] 발견된 태스크 ID들: {found_tasks[:10]}")  # 처음 10개만
            return False
        
        # 새 상태 결정
        if status == "in_progress":
            new_pattern = f"- [~] {task_id}"
        elif status == "completed":
            new_pattern = f"- [x] {task_id}"
        elif status == "not_started":
            new_pattern = f"- [ ] {task_id}"
        else:
            return False
        
        # 상태 변경
        content = content.replace(current_pattern, new_pattern, 1)
        print(f"[DEBUG] 상태 변경: {current_pattern} -> {new_pattern}")
        
        # 진행률 업데이트
        completed_count = content.count("- [x]")
        in_progress_count = content.count("- [~]")
        not_started_count = content.count("- [ ]")
        total_count = completed_count + in_progress_count + not_started_count
        
        print(f"[DEBUG] 진행 상황: 완료={completed_count}, 진행중={in_progress_count}, 미완료={not_started_count}, 전체={total_count}")
        
        if total_count > 0:
            progress = int(completed_count / total_count * 100)
            
            # 진행 상황 섹션 업데이트
            content = re.sub(
                r"- 완료: \d+개",
                f"- 완료: {completed_count}개",
                content
            )
            content = re.sub(
                r"- 진행 중: \d+개",
                f"- 진행 중: {in_progress_count}개",
                content
            )
            content = re.sub(
                r"- 진행률: \d+%",
                f"- 진행률: {progress}%",
                content
            )
        
        with open(tasks_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"[DEBUG] tasks.md 파일 저장 완료")
        return True

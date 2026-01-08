# TaskPlanner 에이전트 - Tasks 문서 생성
# 체크박스 형식의 실행 가능한 태스크 목록 생성

import os
from strands import Agent, tool
from strands_tools import file_read, file_write
from model.load import load_sonnet
from prompts.system_prompts import TASK_PLANNER_PROMPT


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
    
    # 파일별 태스크 생성
    for i, file_path in enumerate(files, start=1):
        # 파일명만 추출
        rel_path = file_path
        if workshop_path in file_path:
            rel_path = file_path.replace(workshop_path, "").lstrip("/")
        
        lines.append(f"- [ ] 2.{i} `{rel_path}` 번역")
        lines.append("  - _Requirements: 1.1, 3.1, 4.1_")
    
    lines.extend([
        "",
        "## Phase 3: 검증",
        "",
        "- [ ] 3.1 구조 검증 (Frontmatter, Markdown 구문)",
        "  - _Requirements: 4.1, 4.2, 6.1_",
        "",
        "- [ ] 3.2 품질 검토 (용어 일관성, 자연스러움)",
        "  - _Requirements: 3.1, 5.1, 5.2_",
        "",
        "- [ ] 3.3 줄 수 비교 검증",
        "  - _Requirements: 6.2, 6.3_",
        "",
        "## Phase 4: 완료",
        "",
        "- [ ] 4.1 최종 보고서 생성",
        "  - _Requirements: 6.5_",
        "",
        "---",
        "",
        "## 진행 상황",
        "",
        f"- 총 태스크: {len(files) + 5}개",
        "- 완료: 0개",
        "- 진행률: 0%",
    ])
    
    content = "\n".join(lines)
    
    # 파일 저장
    if output_path is None:
        output_path = os.path.join(workshop_path, ".kiro", "specs", "translation", "tasks.md")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return {
        "content": content,
        "output_path": output_path,
        "task_count": len(files) + 5,  # 파일 수 + 환경설정 + 검증 태스크
        "file_count": len(files),
    }


def update_task_status(tasks_path: str, task_id: str, completed: bool = True) -> bool:
    """
    태스크 상태를 업데이트합니다.
    
    Args:
        tasks_path: tasks.md 파일 경로
        task_id: 태스크 ID (예: "2.1")
        completed: 완료 여부
    
    Returns:
        bool: 업데이트 성공 여부
    """
    if not os.path.exists(tasks_path):
        return False
    
    with open(tasks_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 상태 변경
    if completed:
        # [ ] → [x]
        old_pattern = f"- [ ] {task_id}"
        new_pattern = f"- [x] {task_id}"
    else:
        # [x] → [ ]
        old_pattern = f"- [x] {task_id}"
        new_pattern = f"- [ ] {task_id}"
    
    if old_pattern not in content:
        return False
    
    content = content.replace(old_pattern, new_pattern)
    
    # 진행률 업데이트
    completed_count = content.count("- [x]")
    total_count = content.count("- [x]") + content.count("- [ ]")
    
    if total_count > 0:
        progress = int(completed_count / total_count * 100)
        
        # 진행 상황 섹션 업데이트
        import re
        content = re.sub(
            r"- 완료: \d+개",
            f"- 완료: {completed_count}개",
            content
        )
        content = re.sub(
            r"- 진행률: \d+%",
            f"- 진행률: {progress}%",
            content
        )
    
    with open(tasks_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return True

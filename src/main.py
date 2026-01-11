# Workshop Translator - Orchestrator 메인 진입점
# 중앙 집중식 상태 관리

import os
from strands import Agent, tool
from strands.agent.conversation_manager import SummarizingConversationManager
from strands_tools import file_read, file_write
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# strands-agents-tools의 도구 동의 절차 우회 설정
os.environ['BYPASS_TOOL_CONSENT'] = 'true'

# 로컬 모듈 임포트
from model.load import load_opus, load_sonnet
from prompts.system_prompts import ORCHESTRATOR_PROMPT

# 분석/설계 도구 (기존)
from agents.analyzer import analyze_workshop
from agents.designer import generate_design

# Orchestrator 도구
from agents.orchestrator import (
    initialize_workflow,
    run_translation_phase,
    run_review_phase,
    run_validate_phase,
    run_preview_phase,
    stop_preview,
    get_workflow_status,
    retry_failed_tasks,
    check_phase_completion,
)

# BedrockAgentCoreApp 인스턴스 생성
app = BedrockAgentCoreApp()
log = app.logger

# 환경 변수
REGION = os.getenv("AWS_REGION", "us-west-2")


@app.entrypoint
async def invoke(payload, context):
    """에이전트 호출 진입점"""
    session_id = getattr(context, 'session_id', 'default')
    prompt = payload.get("prompt", "")
    
    # Conversation Manager 설정
    conversation_manager = SummarizingConversationManager(
        summary_ratio=0.3,
        preserve_recent_messages=10,
        summarization_system_prompt="번역 작업 대화 내용을 간결하게 요약해주세요."
    )
    
    # Orchestrator 에이전트 생성 (Opus 사용)
    agent = Agent(
        model=load_opus(),
        conversation_manager=conversation_manager,
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=[
            # 파일 도구
            file_read,
            file_write,
            # 분석/설계 도구
            analyze_workshop,
            generate_design,
            # Orchestrator 도구
            initialize_workflow,      # 워크플로우 초기화
            run_translation_phase,    # 번역 단계 실행
            run_review_phase,         # 검토 단계 실행
            run_validate_phase,       # 검증 단계 실행
            run_preview_phase,        # 로컬 프리뷰 실행
            stop_preview,             # 프리뷰 종료
            get_workflow_status,      # 상태 조회
            retry_failed_tasks,       # 실패 재시도
            check_phase_completion,   # 단계 완료 확인
        ]
    )
    
    # 스트리밍 응답 실행
    stream = agent.stream_async(prompt)
    
    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]
        elif "current_tool_use" in event:
            tool_use = event["current_tool_use"]
            tool_name = tool_use.get("name", "unknown")
            log.info(f"도구 호출: {tool_name}")


# ANSI 색상 코드
class Colors:
    """터미널 색상 코드"""
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


# 도구별 색상 매핑
TOOL_COLORS = {
    # 분석/설계 도구 - 파란색 계열
    "analyze_workshop": Colors.BLUE,
    "generate_design": Colors.BLUE,
    # 워크플로우 관리 - 마젠타
    "initialize_workflow": Colors.MAGENTA,
    "get_workflow_status": Colors.MAGENTA,
    "check_phase_completion": Colors.MAGENTA,
    "retry_failed_tasks": Colors.MAGENTA,
    # 번역 - 녹색
    "run_translation_phase": Colors.GREEN,
    # 검토 - 노란색
    "run_review_phase": Colors.YELLOW,
    # 검증 - 시안
    "run_validate_phase": Colors.CYAN,
    # 프리뷰 - 녹색 (밝은)
    "run_preview_phase": Colors.GREEN,
    "stop_preview": Colors.RED,
    # 파일 도구 - 흰색 (dim)
    "file_read": Colors.DIM,
    "file_write": Colors.DIM,
}


def get_tool_color(tool_name: str) -> str:
    """도구 이름에 따른 색상 반환"""
    return TOOL_COLORS.get(tool_name, Colors.WHITE)


def print_tool_start(tool_name: str, tool_input: dict = None):
    """도구 호출 시작 메시지 출력"""
    color = get_tool_color(tool_name)
    print(f"\n{color}🔧 [{tool_name}] 실행 중...{Colors.RESET}", flush=True)


def print_tool_end(tool_name: str, success: bool = True, result_summary: str = None):
    """도구 호출 완료 메시지 출력"""
    color = get_tool_color(tool_name)
    status = f"{Colors.GREEN}✓{Colors.RESET}" if success else f"{Colors.RED}✗{Colors.RESET}"
    
    if result_summary:
        print(f"{color}   └─ {status} {result_summary}{Colors.RESET}", flush=True)
    else:
        print(f"{color}   └─ {status} 완료{Colors.RESET}", flush=True)


def tool_callback_handler(**kwargs):
    """
    도구 호출 콜백 핸들러 (함수 기반)
    
    strands-agents의 callback_handler는 함수를 기대합니다.
    """
    # 도구 호출 시작
    if "current_tool_use" in kwargs:
        tool_use = kwargs["current_tool_use"]
        # tool_use가 dict인 경우에만 처리
        if isinstance(tool_use, dict):
            tool_name = tool_use.get("name", "")
            tool_input = tool_use.get("input", {})
            
            if tool_name:
                # file_read/file_write는 간략하게 표시
                if tool_name in ["file_read", "file_write"]:
                    if isinstance(tool_input, dict):
                        path = tool_input.get("path", tool_input.get("file_path", ""))
                        if path:
                            if len(path) > 50:
                                path = "..." + path[-47:]
                            print(f"{Colors.DIM}   📄 {tool_name}: {path}{Colors.RESET}", flush=True)
                else:
                    print_tool_start(tool_name, tool_input)
    
    # 텍스트 출력 (data 이벤트)
    if "data" in kwargs:
        print(kwargs["data"], end="", flush=True)


def run_cli():
    """CLI 모드로 실행합니다."""
    print("=" * 60)
    print("Workshop Translator Agent (Orchestrator Pattern)")
    print("=" * 60)
    print("\n안녕하세요! AWS Workshop 번역을 도와드리겠습니다.")
    print("💡 중앙 집중식 워크플로우입니다.")
    print("\n⚠️  AWS 인증 정보가 필요합니다 (Bedrock 호출용)")
    print("   - AWS CLI 설정: aws configure")
    print("   - 또는 환경 변수: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
    print("   - 리전 설정: AWS_REGION (기본값: us-west-2)")
    print("\n📋 워크플로우:")
    print("  1. analyze_workshop → 구조 분석")
    print("  2. generate_design → 설계 문서 생성")
    print("  3. initialize_workflow → 태스크 초기화")
    print("  4. run_translation_phase → 번역 실행")
    print("  5. run_review_phase → 품질 검토")
    print("  6. run_validate_phase → 구조 검증")
    print("  7. run_preview_phase → 로컬 프리뷰")
    print("\n종료하려면 'exit' 또는 'quit'를 입력하세요.\n")
    
    # Conversation Manager 설정
    conversation_manager = SummarizingConversationManager(
        summary_ratio=0.3,
        preserve_recent_messages=10,
        summarization_system_prompt="번역 작업 대화 내용을 간결하게 요약해주세요."
    )
    
    # Orchestrator 에이전트 생성 (CLI에서는 Sonnet 사용)
    agent = Agent(
        model=load_sonnet(),
        conversation_manager=conversation_manager,
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=[
            file_read,
            file_write,
            analyze_workshop,
            generate_design,
            # Orchestrator 도구
            initialize_workflow,
            run_translation_phase,
            run_review_phase,
            run_validate_phase,
            run_preview_phase,
            stop_preview,
            get_workflow_status,
            retry_failed_tasks,
            check_phase_completion,
        ],
        callback_handler=tool_callback_handler,
    )
    
    while True:
        try:
            user_input = input("\n사용자: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit", "종료"]:
                print("\n감사합니다. 안녕히 가세요!")
                break
            
            print(f"\n{Colors.CYAN}{Colors.BOLD}Orchestrator:{Colors.RESET} ", end="", flush=True)
            
            try:
                response = agent(user_input)
            except Exception as e:
                raise e
            
            print()
                
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}중단되었습니다.{Colors.RESET}")
            break
        except Exception as e:
            print(f"\n{Colors.RED}오류 발생: {e}{Colors.RESET}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        run_cli()
    else:
        app.run()

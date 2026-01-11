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


class ToolCallbackHandler:
    """도구 호출 콜백 핸들러"""
    
    def __init__(self):
        self._current_tool = None
    
    def on_tool_start(self, tool_name: str, tool_input: dict, **kwargs):
        """도구 실행 시작 시 호출"""
        self._current_tool = tool_name
        # file_read/file_write는 너무 자주 호출되므로 간략하게 표시
        if tool_name in ["file_read", "file_write"]:
            path = tool_input.get("path", tool_input.get("file_path", ""))
            if path:
                # 경로가 길면 축약
                if len(path) > 50:
                    path = "..." + path[-47:]
                print(f"{Colors.DIM}   📄 {tool_name}: {path}{Colors.RESET}", flush=True)
        else:
            print_tool_start(tool_name, tool_input)
    
    def on_tool_end(self, tool_name: str, tool_output: any, **kwargs):
        """도구 실행 완료 시 호출"""
        # file_read/file_write는 완료 메시지 생략
        if tool_name in ["file_read", "file_write"]:
            return
        
        # 결과 요약 생성
        summary = None
        if isinstance(tool_output, dict):
            if "message" in tool_output:
                summary = tool_output["message"]
            elif "progress" in tool_output:
                prog = tool_output["progress"]
                if isinstance(prog, dict):
                    summary = f"진행률: {prog.get('progress_percent', 0)}%"
            elif "phase_progress" in tool_output:
                prog = tool_output["phase_progress"]
                if isinstance(prog, dict):
                    summary = f"완료: {prog.get('completed', 0)}/{prog.get('total', 0)}"
        
        print_tool_end(tool_name, success=True, result_summary=summary)
        self._current_tool = None
    
    def on_tool_error(self, tool_name: str, error: Exception, **kwargs):
        """도구 실행 오류 시 호출"""
        print_tool_end(tool_name, success=False, result_summary=str(error)[:50])
        self._current_tool = None


class ColoredOutput:
    """stdout을 래핑하여 출력에 색상을 추가하는 클래스"""
    def __init__(self, original_stdout, color):
        self.original_stdout = original_stdout
        self.color = color
        self.reset = Colors.RESET
        
    def write(self, text):
        if text and text.strip():
            if '\033[' in text:
                self.original_stdout.write(text)
            else:
                self.original_stdout.write(f"{self.color}{text}{self.reset}")
        else:
            self.original_stdout.write(text)
        self.original_stdout.flush()
    
    def flush(self):
        self.original_stdout.flush()


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
            get_workflow_status,
            retry_failed_tasks,
            check_phase_completion,
        ],
        callback_handler=ToolCallbackHandler(),
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
            
            import sys
            original_stdout = sys.stdout
            sys.stdout = ColoredOutput(original_stdout, Colors.CYAN)
            
            try:
                response = agent(user_input)
            finally:
                sys.stdout = original_stdout
            
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

# Workshop Translator - Orchestrator 메인 진입점
# Sisyphus 패턴 참고: 대화형 인터페이스, 자동 진행, Todo 추적

import os
from strands import Agent, tool
from strands.agent.conversation_manager import SummarizingConversationManager
from strands_tools import file_read, file_write
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# strands-agents-tools의 도구 동의 절차 우회 설정
# file_read, file_write 등의 도구를 자동으로 승인하여 사용자 확인 없이 실행
os.environ['BYPASS_TOOL_CONSENT'] = 'true'

# 로컬 모듈 임포트
from model.load import load_opus, load_sonnet
from prompts.system_prompts import ORCHESTRATOR_PROMPT

# 서브에이전트 도구 임포트
from agents.analyzer import analyze_workshop
from agents.designer import generate_design
from agents.task_planner import generate_tasks, update_task_status
from agents.translator import translate_file, translate_files_parallel, check_background_tasks
from agents.reviewer import review_file, review_files_parallel, review_all_translations
from agents.validator import validate_file, validate_files_parallel, validate_structure

# BedrockAgentCoreApp 인스턴스 생성
app = BedrockAgentCoreApp()
log = app.logger

# 환경 변수
REGION = os.getenv("AWS_REGION", "us-west-2")


@app.entrypoint
async def invoke(payload, context):
    """에이전트 호출 진입점"""
    # 세션 ID 가져오기
    session_id = getattr(context, 'session_id', 'default')
    
    # 프롬프트 가져오기
    prompt = payload.get("prompt", "")
    
    # Conversation Manager 설정 (긴 대화 관리)
    conversation_manager = SummarizingConversationManager(
        summary_ratio=0.3,
        preserve_recent_messages=10,
        summarization_system_prompt="번역 작업 대화 내용을 간결하게 요약해주세요."
    )
    
    # Orchestrator 에이전트 생성
    # Opus 4.5 사용 (extended thinking 지원)
    agent = Agent(
        model=load_opus(),
        conversation_manager=conversation_manager,
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=[
            # 파일 도구
            file_read,
            file_write,
            # 서브에이전트 도구 (Agent as Tool)
            analyze_workshop,
            generate_design,
            generate_tasks,
            # 번역 도구
            translate_file,
            translate_files_parallel,
            check_background_tasks,  # 백그라운드 작업 상태 확인
            # 검토 도구
            review_file,
            review_files_parallel,
            review_all_translations,
            # 검증 도구
            validate_file,
            validate_files_parallel,
            validate_structure,
        ]
    )
    
    # 스트리밍 응답 실행
    stream = agent.stream_async(prompt)
    
    async for event in stream:
        # 텍스트 응답 처리
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]
        
        # 도구 호출 로깅 (디버그용)
        elif "current_tool_use" in event:
            tool_use = event["current_tool_use"]
            tool_name = tool_use.get("name", "unknown")
            log.info(f"도구 호출: {tool_name}")


# ANSI 색상 코드
class Colors:
    """터미널 색상 코드"""
    CYAN = '\033[96m'      # Orchestrator 메시지용 (밝은 청록색)
    GREEN = '\033[92m'     # 성공 메시지용
    YELLOW = '\033[93m'    # 경고 메시지용
    RED = '\033[91m'       # 에러 메시지용
    BLUE = '\033[94m'      # 도구 호출용
    MAGENTA = '\033[95m'   # 진행 상황용
    RESET = '\033[0m'      # 색상 리셋
    BOLD = '\033[1m'       # 굵게


class ColoredOutput:
    """stdout을 래핑하여 출력에 색상을 추가하는 클래스"""
    def __init__(self, original_stdout, color):
        self.original_stdout = original_stdout
        self.color = color
        self.reset = Colors.RESET
        
    def write(self, text):
        """텍스트를 색상과 함께 출력"""
        if text and text.strip():  # 빈 문자열이 아닌 경우에만 색상 적용
            # 이미 색상 코드가 있는지 확인 (DEBUG 메시지 등)
            if '\033[' in text:
                # 이미 색상이 있으면 그대로 출력
                self.original_stdout.write(text)
            else:
                # 색상 추가
                self.original_stdout.write(f"{self.color}{text}{self.reset}")
        else:
            # 빈 문자열이나 공백은 그대로 출력
            self.original_stdout.write(text)
        self.original_stdout.flush()
    
    def flush(self):
        """버퍼 플러시"""
        self.original_stdout.flush()


# 로컬 실행용 CLI 인터페이스
def run_cli():
    """CLI 모드로 실행합니다."""
    print("=" * 60)
    print("Workshop Translator Agent")
    print("=" * 60)
    print("\n안녕하세요! AWS Workshop 번역을 도와드리겠습니다.")
    print("💡 이 도구는 AWS Bedrock을 사용합니다. AWS 자격 증명이 필요합니다.")
    print("   (aws configure 또는 환경 변수로 설정)")
    print("\n종료하려면 'exit' 또는 'quit'를 입력하세요.\n")
    
    # Conversation Manager 설정
    conversation_manager = SummarizingConversationManager(
        summary_ratio=0.3,
        preserve_recent_messages=10,
        summarization_system_prompt="번역 작업 대화 내용을 간결하게 요약해주세요."
    )
    
    # Orchestrator 에이전트 생성
    agent = Agent(
        model=load_sonnet(),  # CLI에서는 Sonnet 사용 (비용 절감)
        conversation_manager=conversation_manager,
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=[
            file_read,
            file_write,
            analyze_workshop,
            generate_design,
            generate_tasks,
            # 번역 도구
            translate_file,
            translate_files_parallel,
            check_background_tasks,  # 백그라운드 작업 상태 확인
            # 검토 도구
            review_file,
            review_files_parallel,
            review_all_translations,
            # 검증 도구
            validate_file,
            validate_files_parallel,
            validate_structure,
        ]
    )
    
    while True:
        try:
            user_input = input("\n사용자: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit", "종료"]:
                print("\n감사합니다. 안녕히 가세요!")
                break
            
            # Orchestrator 레이블 출력 (색상 적용)
            print(f"\n{Colors.CYAN}{Colors.BOLD}Orchestrator:{Colors.RESET} ", end="", flush=True)
            
            # stdout을 색상 래퍼로 교체
            import sys
            original_stdout = sys.stdout
            sys.stdout = ColoredOutput(original_stdout, Colors.CYAN)
            
            try:
                # 에이전트 실행 (출력이 자동으로 색상 적용됨)
                response = agent(user_input)
            finally:
                # 원래 stdout 복원
                sys.stdout = original_stdout
            
            # 응답이 반환되면 줄바꿈
            print()
                
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}중단되었습니다.{Colors.RESET}")
            break
        except Exception as e:
            print(f"\n{Colors.RED}오류 발생: {e}{Colors.RESET}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        # CLI 모드 실행
        run_cli()
    else:
        # AgentCore Runtime 모드 실행
        app.run()

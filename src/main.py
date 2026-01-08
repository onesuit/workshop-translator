# Workshop Translator - Orchestrator 메인 진입점
# Sisyphus 패턴 참고: 대화형 인터페이스, 자동 진행, Todo 추적

import os
from strands import Agent, tool
from strands.agent.conversation_manager import SummarizingConversationManager
from strands_tools import file_read, file_write
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# 로컬 모듈 임포트
from model.load import load_opus, load_sonnet
from prompts.system_prompts import ORCHESTRATOR_PROMPT

# 서브에이전트 도구 임포트
from agents.analyzer import analyze_workshop
from agents.designer import generate_design
from agents.task_planner import generate_tasks, update_task_status
from agents.translator import translate_file, translate_files_parallel, check_background_tasks
from agents.reviewer import review_translation, review_all_translations
from agents.validator import validate_structure

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
            translate_file,
            translate_files_parallel,
            check_background_tasks,  # 백그라운드 작업 상태 확인
            review_translation,
            review_all_translations,
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


# 로컬 실행용 CLI 인터페이스
def run_cli():
    """CLI 모드로 실행합니다."""
    print("=" * 60)
    print("Workshop Translator Agent")
    print("=" * 60)
    print("\n안녕하세요! Workshop 번역을 도와드리겠습니다.")
    print("종료하려면 'exit' 또는 'quit'를 입력하세요.\n")
    
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
            translate_file,
            translate_files_parallel,
            check_background_tasks,  # 백그라운드 작업 상태 확인
            review_translation,
            review_all_translations,
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
            
            # 에이전트 실행 (Strands가 자동으로 스트리밍 출력)
            response = agent(user_input)
                
        except KeyboardInterrupt:
            print("\n\n중단되었습니다.")
            break
        except Exception as e:
            print(f"\n오류 발생: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        # CLI 모드 실행
        run_cli()
    else:
        # AgentCore Runtime 모드 실행
        app.run()

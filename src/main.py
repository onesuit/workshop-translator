# Workshop Translator - Orchestrator main entry point
# Centralized state management

import os
from strands import Agent, tool
from strands.agent.conversation_manager import SummarizingConversationManager
from strands_tools import file_read, file_write
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Bypass strands-agents-tools consent procedure
os.environ['BYPASS_TOOL_CONSENT'] = 'true'

# Local module imports
from model.load import load_opus, load_sonnet
from prompts.system_prompts import ORCHESTRATOR_PROMPT

# Analysis/Design tools (existing)
from agents.analyzer import analyze_workshop
from agents.designer import generate_design

# Orchestrator tools
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

# BedrockAgentCoreApp instance
app = BedrockAgentCoreApp()
log = app.logger

# Environment variables
REGION = os.getenv("AWS_REGION", "us-west-2")


@app.entrypoint
async def invoke(payload, context):
    """Agent invocation entry point"""
    session_id = getattr(context, 'session_id', 'default')
    prompt = payload.get("prompt", "")
    
    # Conversation Manager setup
    conversation_manager = SummarizingConversationManager(
        summary_ratio=0.3,
        preserve_recent_messages=10,
        summarization_system_prompt="Summarize the translation task conversation concisely."
    )
    
    # Orchestrator agent creation (using Opus)
    agent = Agent(
        model=load_opus(),
        conversation_manager=conversation_manager,
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=[
            # File tools
            file_read,
            file_write,
            # Analysis/Design tools
            analyze_workshop,
            generate_design,
            # Orchestrator tools
            initialize_workflow,      # Initialize workflow
            run_translation_phase,    # Run translation phase
            run_review_phase,         # Run review phase
            run_validate_phase,       # Run validation phase
            run_preview_phase,        # Run local preview
            stop_preview,             # Stop preview
            get_workflow_status,      # Get status
            retry_failed_tasks,       # Retry failed tasks
            check_phase_completion,   # Check phase completion
        ]
    )
    
    # Streaming response execution
    stream = agent.stream_async(prompt)
    
    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]
        elif "current_tool_use" in event:
            tool_use = event["current_tool_use"]
            tool_name = tool_use.get("name", "unknown")
            log.info(f"Tool call: {tool_name}")


def sanitize_input(text: str) -> str:
    """
    Remove characters from user input that cause JSON serialization issues.
    Handles hidden control characters that may be included during copy/paste.
    """
    if not text:
        return text
    
    # Remove NULL bytes
    text = text.replace('\x00', '')
    
    # Remove control characters that cause JSON serialization issues (except tab, newline)
    text = ''.join(
        char for char in text 
        if char >= ' ' or char in '\t\n\r'
    )
    
    return text.strip()


# ANSI color codes
class Colors:
    """Terminal color codes"""
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


# Tool color mapping
TOOL_COLORS = {
    # Analysis/Design tools - blue
    "analyze_workshop": Colors.BLUE,
    "generate_design": Colors.BLUE,
    # Workflow management - magenta
    "initialize_workflow": Colors.MAGENTA,
    "get_workflow_status": Colors.MAGENTA,
    "check_phase_completion": Colors.MAGENTA,
    "retry_failed_tasks": Colors.MAGENTA,
    # Translation - green
    "run_translation_phase": Colors.GREEN,
    # Review - yellow
    "run_review_phase": Colors.YELLOW,
    # Validation - cyan
    "run_validate_phase": Colors.CYAN,
    # Preview - green (bright)
    "run_preview_phase": Colors.GREEN,
    "stop_preview": Colors.RED,
    # File tools - white (dim)
    "file_read": Colors.DIM,
    "file_write": Colors.DIM,
}


def get_tool_color(tool_name: str) -> str:
    """Return color based on tool name"""
    return TOOL_COLORS.get(tool_name, Colors.WHITE)


def print_tool_start(tool_name: str, tool_input: dict = None):
    """Print tool execution start message"""
    color = get_tool_color(tool_name)
    print(f"\n{color}🔧 [{tool_name}] Running...{Colors.RESET}", flush=True)


def print_tool_end(tool_name: str, success: bool = True, result_summary: str = None):
    """Print tool execution completion message"""
    color = get_tool_color(tool_name)
    status = f"{Colors.GREEN}✓{Colors.RESET}" if success else f"{Colors.RED}✗{Colors.RESET}"
    
    if result_summary:
        print(f"{color}   └─ {status} {result_summary}{Colors.RESET}", flush=True)
    else:
        print(f"{color}   └─ {status} Done{Colors.RESET}", flush=True)


def tool_callback_handler(**kwargs):
    """
    Tool call callback handler (function-based)
    
    strands-agents callback_handler expects a function.
    """
    # Tool call start
    if "current_tool_use" in kwargs:
        tool_use = kwargs["current_tool_use"]
        # Only process if tool_use is a dict
        if isinstance(tool_use, dict):
            tool_name = tool_use.get("name", "")
            tool_input = tool_use.get("input", {})
            
            if tool_name:
                # Show file_read/file_write briefly
                if tool_name in ["file_read", "file_write"]:
                    if isinstance(tool_input, dict):
                        path = tool_input.get("path", tool_input.get("file_path", ""))
                        if path:
                            if len(path) > 50:
                                path = "..." + path[-47:]
                            print(f"{Colors.DIM}   📄 {tool_name}: {path}{Colors.RESET}", flush=True)
                else:
                    print_tool_start(tool_name, tool_input)
    
    # Text output (data event)
    if "data" in kwargs:
        print(kwargs["data"], end="", flush=True)


def run_cli():
    """Run in CLI mode."""
    print("=" * 60)
    print("Workshop Translator Agent")
    print("=" * 60)
    print("\nWelcome! I'll help you translate AWS Workshop documents.")
    print("\n⚠️  Prerequisites:")
    print("   - AWS credentials with Bedrock access permissions")
    print("   - Configure via: aws configure (or isengardcli)")
    print("   - Region setting: AWS_REGION (default: us-west-2)")
    print("\n📋 To get started, please provide:")
    print("   1. Workshop path (local directory path)")
    print("   2. Target language(s) for translation")
    print("\n💡 Note: If the session ends and restarts, please provide")
    print("   the workshop path again.")
    print("\nType 'exit' or 'quit' to end the session.\n")
    
    # Conversation Manager setup
    conversation_manager = SummarizingConversationManager(
        summary_ratio=0.3,
        preserve_recent_messages=10,
        summarization_system_prompt="Summarize the translation task conversation concisely."
    )
    
    # Orchestrator agent creation (using Sonnet for CLI)
    agent = Agent(
        model=load_sonnet(),
        conversation_manager=conversation_manager,
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=[
            file_read,
            file_write,
            analyze_workshop,
            generate_design,
            # Orchestrator tools
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
            user_input = sanitize_input(input("\nUser: "))
            
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit"]:
                print("\nThank you. Goodbye!")
                break
            
            print(f"\n{Colors.CYAN}{Colors.BOLD}Orchestrator:{Colors.RESET} ", end="", flush=True)
            
            try:
                response = agent(user_input)
            except Exception as e:
                # Remove last user message to recover state on error
                if agent.messages and agent.messages[-1]["role"] == "user":
                    agent.messages.pop()
                print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")
                print(f"{Colors.YELLOW}💡 Conversation state recovered. Please try again.{Colors.RESET}")
                continue
            
            print()
                
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Interrupted.{Colors.RESET}")
            break
        except Exception as e:
            print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        run_cli()
    else:
        app.run()

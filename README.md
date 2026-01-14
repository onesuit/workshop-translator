# Workshop Translator

🌐 **Language**: English | [한국어](https://github.com/onesuit/workshop-translator/blob/main/README.ko.md)

AI-powered CLI tool for automatically translating AWS Workshop documents.

## Key Features

- 🤖 **AI-Powered Translation**: High-quality translation using Claude models (Opus/Sonnet/Haiku)
- 📚 **AWS Documentation Integration**: Accurate terminology via MCP integration with official AWS docs
- ⚡ **Parallel Processing**: Process up to 5 files simultaneously with ThreadPoolExecutor
- 🔄 **Session Resume**: Continue interrupted work from where you left off
- 📊 **Quality Management**: 3-stage workflow: Translation → Review → Validation
- 👀 **Local Preview**: Instantly preview translation results

## Architecture

Uses an **Orchestrator-centric architecture**.

```
┌─────────────────────────────────────────────────────────────────┐
│                      Orchestrator (main.py)                      │
│                    Claude Opus / Sonnet                          │
│                                                                  │
│  Core Principle: Only Orchestrator modifies tasks.md             │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │   TaskManager     │
                    │   (Singleton)     │
                    │                   │
                    │ • Task state mgmt │
                    │ • Dependency check│
                    │ • tasks.md sync   │
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Translator   │    │   Reviewer    │    │   Validator   │
│    Worker     │    │    Worker     │    │    Worker     │
│  (Stateless)  │    │  (Stateless)  │    │  (Stateless)  │
│ Returns only  │    │ Returns only  │    │ Returns only  │
│   results     │    │   results     │    │   results     │
└───────────────┘    └───────────────┘    └───────────────┘
```

### Core Design Principles

| Item | Description |
|------|-------------|
| **Centralized State Management** | Only Orchestrator (TaskManager) modifies tasks.md |
| **Stateless Workers** | Sub-agents return results only, no direct state file modification |
| **Automatic Dependency Management** | TaskManager automatically checks inter-task dependencies |
| **Parallel Processing** | Up to 5 files processed simultaneously via ThreadPoolExecutor |
| **Session Resume** | Load existing tasks.md state to continue work |

## Model Configuration

| Model | Purpose | Features |
|-------|---------|----------|
| **Claude Opus 4.5** | Orchestrator (remote mode) | Extended thinking support |
| **Claude Sonnet 4.5** | Designer, Translator, Reviewer | Balanced performance |
| **Claude Haiku 4.5** | Analyzer | Fast processing |

## Workflow

```
Phase 1: Analysis/Design
    ├── analyze_workshop()     → Analyze workshop structure
    └── generate_design()      → Generate design document
           │
           ▼
Phase 2: Workflow Initialization
    └── initialize_workflow()  → Initialize TaskManager, create tasks.md
           │
           ▼
Phase 3: Translation
    └── run_translation_phase() → Execute parallel translation
           │
           ▼
Phase 4: Review
    └── run_review_phase()     → Review completed translations only
           │                   → Generate review_report.md
           ▼
Phase 5: Validation
    └── run_validate_phase()   → Validate translated+reviewed files only
           │                   → Generate validate_report.md
           ▼
Phase 6: Preview
    └── run_preview_phase()    → Run local preview server
           │                   → http://localhost:8080
           ▼
Phase 7: Complete
    └── get_workflow_status()  → Final status report
```

## Orchestrator Tools

| Tool | Description |
|------|-------------|
| `analyze_workshop` | Analyze workshop structure, return target file list |
| `generate_design` | Generate translation design document |
| `initialize_workflow` | Initialize workflow, create tasks.md |
| `run_translation_phase` | Execute translation phase in parallel |
| `run_review_phase` | Execute review phase in parallel, generate review_report.md |
| `run_validate_phase` | Execute validation phase in parallel, generate validate_report.md |
| `run_preview_phase` | Run local preview server (background) |
| `stop_preview` | Stop preview server |
| `get_workflow_status` | Query overall progress |
| `retry_failed_tasks` | Retry failed tasks |
| `check_phase_completion` | Check phase completion status |

## Generated Files

The following files are created in the `translation/` directory during translation:

| File | Description |
|------|-------------|
| `design.md` | Translation design document |
| `tasks.md` | Task progress status (checkbox format) |
| `review_report.md` | Review phase report (scores, PASS/FAIL list) |
| `validate_report.md` | Validation phase report (structure validation results) |

## Installation

### Install from PyPI (Recommended)

```bash
# Using uvx (run without installation)
uvx wstranslator

# Or install via pip
pip install wstranslator
wstranslator
```

### Development Mode (Local Development)

```bash
# After cloning the repository
cd workshop-translator/WsTranslator

# Using uv
uv sync
uv run wstranslator

# Or using pip
pip install -e .
wstranslator
```

## Usage

### Interactive Mode

```bash
wstranslator
```

In interactive mode, the Orchestrator automatically progresses through the workflow.

**Example conversation:**
```
User: Please translate the /path/to/workshop directory to Korean

Orchestrator: Analyzing workshop structure...
              → Found 10 files
              → Workflow initialization complete
              → Starting translation (5 files in parallel)
              → Translation complete: 10/10 (100%)
              → Starting review...
              → Review complete. review_report.md generated
              → Validation complete. validate_report.md generated
              → Preview server started: http://localhost:8080
```

### Session Resume

You can continue interrupted work from a previous session:

```
User: Please continue the previous translation work

Orchestrator: Resuming existing workflow. Loaded 25/30 tasks completed.
              → Starting translation of remaining 5 files...
```

## Requirements

- Python 3.10+
- AWS credentials configured (AWS CLI or environment variables)
- Bedrock model access (Claude Opus, Sonnet, Haiku)

## Environment Variables

```bash
# AWS region setting (default: us-west-2)
export AWS_REGION=us-west-2

# AWS profile setting
export AWS_PROFILE=your-profile
```

## Dependencies

Key packages:
- `strands-agents`: AI agent framework
- `strands-agents-tools`: File read/write tools
- `bedrock-agentcore`: AWS Bedrock AgentCore runtime
- `mcp`: Model Context Protocol client
- `boto3`: AWS SDK

## Troubleshooting

### AWS Credentials Error
```bash
# AWS CLI configuration
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-west-2
```

### Preview Server Error
```bash
# On macOS with execution permission issues
# Control-click preview_build file in Finder → Open

# File open limit error
ulimit -n 10240
```

### MCP Connection Error
```bash
# Check uvx installation
uvx --version

# Test AWS Documentation MCP server
uvx awslabs.aws-documentation-mcp-server@latest
```

## Developer Information

- **Author**: Jisan Bang (wltks2155@gmail.com)
- **GitHub**: https://github.com/onesuit/workshop-translator
- **License**: MIT
- **Python Version**: 3.10+

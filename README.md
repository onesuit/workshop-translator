# Workshop Translator Agent

AWS Workshop 콘텐츠를 다국어로 번역하는 Spec-driven 멀티 에이전트 시스템입니다.

## 개요

Kiro의 Spec 방식(requirements → design → tasks)을 Agent로 자동화합니다.
oh-my-opencode 패턴(Sisyphus, Oracle, Librarian, Explore, Document Writer)을 참고하여 설계되었습니다.

## 에이전트 구조

| Agent | 모델 | 역할 |
|-------|------|------|
| Orchestrator | Opus 4.5 | 대화형 인터페이스, 워크플로우 조율 |
| Analyzer | Haiku | Workshop 구조 분석 |
| Designer | Sonnet 4.5 | Design 문서 생성 |
| TaskPlanner | Sonnet 4.5 | Tasks 문서 생성 |
| Translator | Sonnet 4.5 | 실제 번역 (병렬) |
| Reviewer | Sonnet 4.5 | 품질 검토 |
| Validator | Haiku | 구조 검증 |

## 설치

```bash
# Python 3.13 가상환경 생성
python3.13 -m venv .venv
source .venv/bin/activate

# 패키지 설치
pip install -e .
```

## 사용법

### CLI 모드

```bash
cd src
python main.py cli
```

### AgentCore Runtime 모드

```bash
agentcore local run
```

## 대화 예시

```
사용자: 번역 시작

에이전트: 안녕하세요! Workshop 번역을 도와드리겠습니다.
         어떤 Workshop 디렉토리를 번역할까요?

사용자: /path/to/workshop

에이전트: 타겟 언어를 선택해주세요. (예: ko, ja, zh)

사용자: ko

에이전트: 분석을 시작합니다...
         40개 파일을 발견했습니다.
         Design 문서를 생성합니다...
         Tasks 문서를 생성합니다...
         번역을 시작합니다... (병렬 처리)
         품질 검토 중...
         구조 검증 중...
         
         ✅ 번역 완료!
         - 번역된 파일: 40개
         - 품질 점수: 92/100
         - 검증 결과: PASS
```

## 프로젝트 구조

```
WsTranslator/
├── src/
│   ├── main.py                    # Orchestrator 진입점
│   ├── agents/
│   │   ├── analyzer.py            # @tool - 구조 분석
│   │   ├── designer.py            # @tool - Design 생성
│   │   ├── task_planner.py        # @tool - Tasks 생성
│   │   ├── translator.py          # @tool - 번역 (병렬)
│   │   ├── reviewer.py            # @tool - 품질 검토
│   │   └── validator.py           # @tool - 구조 검증
│   ├── prompts/
│   │   ├── requirements.md        # 재사용 가능한 요구사항
│   │   └── system_prompts.py      # 각 에이전트 시스템 프롬프트
│   ├── tools/
│   │   └── file_tools.py          # 파일 읽기/쓰기
│   ├── mcp_client/
│   │   └── client.py              # AWS Docs + Context7 MCP
│   └── model/
│       └── load.py                # 다중 모델 로드
├── DESIGN_SPEC.md                 # 설계 명세서
├── .bedrock_agentcore.yaml
└── pyproject.toml
```

## MCP 연동

AWS Documentation MCP와 Context7을 연동하여 정확한 AWS 용어를 사용합니다.

`.kiro/settings/mcp.json`:
```json
{
  "mcpServers": {
    "aws-docs": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"]
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@context7/mcp-server"]
    }
  }
}
```

## 지원 언어

- ko (한국어)
- ja (日本語)
- zh (中文)
- es (Español)
- fr (Français)
- de (Deutsch)
- pt (Português)

## 라이선스

Amazon Internal

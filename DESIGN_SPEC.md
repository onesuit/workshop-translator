# Workshop Translator Agent - 설계 명세서

## 개요

AWS Workshop 콘텐츠를 다국어로 번역하는 Spec-driven 멀티 에이전트 시스템입니다.
Kiro의 Spec 방식(requirements → design → tasks)을 Agent로 자동화합니다.

## 참고 자료

- **oh-my-opencode**: 멀티 에이전트 오케스트레이션 패턴
- **기존 Spec 예시**: `ses_expert/.kiro/specs/korean-translation/`
- **AgentCore 기본 템플릿**: `agent/basic/src/main.py`

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                 Orchestrator (Opus 4.5)                     │
│  - 대화형 인터페이스 (디렉토리, 언어 질문)                      │
│  - ConversationManager (컨텍스트 관리)                       │
│  - 서브에이전트 Tool 호출                                     │
│  - Todo 추적 및 자동 진행                                     │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            ┌─────────────┐      ┌─────────────┐
            │  MCP Tools  │      │ Agent Tools │
            ├─────────────┤      ├─────────────┤
            │ AWS Docs    │      │ analyzer    │
            │ Context7    │      │ designer    │
            └─────────────┘      │ task_planner│
                                 │ translator  │
                                 │ reviewer    │
                                 │ validator   │
                                 └─────────────┘
```

---

## 에이전트 상세 설계

### 1. Orchestrator (메인 에이전트)

**모델**: `anthropic/claude-opus-4-5` (extended thinking 32k)

**역할**:
- 사용자와 대화형 인터페이스
- Workshop 디렉토리 및 타겟 언어 확인
- 서브에이전트에 태스크 위임 (직접 번역 안 함)
- Todo 추적 및 완료까지 자동 진행

**프롬프트 핵심 (Sisyphus 참고)**:
```
<Role>
Workshop Translator Orchestrator - 번역 워크플로우 조율자

**Core Competencies**:
- 사용자 요청에서 암묵적 요구사항 파악
- 적절한 서브에이전트에 작업 위임
- 병렬 실행으로 최대 처리량 달성
- Todo 기반 작업 추적

**Operating Mode**: 
직접 번역하지 않음. 항상 전문 서브에이전트에 위임.
</Role>

<Workflow>
Phase 0: 사용자 입력 확인
- Workshop 디렉토리 경로
- 타겟 언어 (ko, ja, zh 등)

Phase 1: 분석
- Analyzer로 Workshop 구조 파악
- 번역 대상 파일 목록 생성

Phase 2: Spec 생성
- Designer로 design.md 생성
- TaskPlanner로 tasks.md 생성

Phase 3: 번역 실행
- Translator로 병렬 번역
- Reviewer로 품질 검토
- Validator로 구조 검증

Phase 4: 완료
- 모든 태스크 완료 확인
- 최종 보고서 생성
</Workflow>
```

---

### 2. Analyzer (구조 분석)

**모델**: `anthropic/claude-haiku-4-5` (빠른 탐색)

**역할**:
- Workshop 디렉토리 구조 스캔
- 번역 대상 파일 식별 (.en.md 파일)
- contentspec.yaml 분석

**프롬프트 핵심 (Explore 참고)**:
```
Workshop 구조 분석 전문가. 번역 대상 파일을 찾아 구조화된 결과 반환.

## Mission
- "어떤 파일을 번역해야 하나요?" 질문에 답변
- Workshop 디렉토리 구조 파악
- .en.md 파일 목록 생성

## CRITICAL: 필수 결과 형식

<analysis>
**Workshop 경로**: [경로]
**contentspec.yaml**: [지원 언어 목록]
**번역 대상 파일 수**: [N개]
</analysis>

<results>
<files>
- /path/to/content/index.en.md
- /path/to/content/1-introduction/index.en.md
...
</files>

<structure>
[디렉토리 구조 트리]
</structure>
</results>
```

---

### 3. Designer (Design 문서 생성)

**모델**: `anthropic/claude-sonnet-4-5`

**역할**:
- requirements.md 기반 design.md 생성
- 아키텍처, 컴포넌트, 용어집 정의

**프롬프트 핵심 (Oracle 참고)**:
```
기술 설계 전문가. Workshop 번역을 위한 Design 문서 생성.

## Decision Framework

**Bias toward simplicity**: 최소한의 복잡성으로 요구사항 충족
**Leverage what exists**: 기존 패턴 활용 (다른 언어 번역 참고)
**One clear path**: 단일 명확한 접근 방식 제시

## Output Structure

1. Overview
2. Architecture (Mermaid 다이어그램)
3. File Structure Design
4. Technical Term Glossary
5. Translation Rules
6. Testing Strategy

## Effort Estimate
- Quick(<1h), Short(1-4h), Medium(1-2d), Large(3d+)
```

---

### 4. TaskPlanner (Tasks 문서 생성)

**모델**: `anthropic/claude-sonnet-4-5`

**역할**:
- design.md 기반 tasks.md 생성
- 체크박스 형식의 태스크 목록

**프롬프트 핵심**:
```
태스크 분해 전문가. Design 문서를 실행 가능한 태스크로 분해.

## Output Format

# Implementation Plan

- [ ] 1. 태스크 제목
  - [ ] 1.1 서브태스크
  - [ ] 1.2 서브태스크
  - _Requirements: X.X, X.X_

## Rules
- 각 태스크는 원자적 (하나의 파일 또는 하나의 작업)
- 병렬 실행 가능한 태스크 그룹화
- 의존성 명시
```

---

### 5. Translator (번역 실행)

**모델**: `anthropic/claude-sonnet-4-5`

**역할**:
- .en.md → .{target_lang}.md 번역
- 병렬 처리 지원

**프롬프트 핵심 (Document Writer 참고)**:
```
기술 번역 전문가. AWS Workshop 콘텐츠를 정확하고 자연스럽게 번역.

## CODE OF CONDUCT

### 1. DILIGENCE & INTEGRITY
- 요청된 작업 완료까지 진행
- 검증 없이 완료 표시 금지

### 2. PRECISION & ADHERENCE TO STANDARDS
- Markdown 구조 유지
- Frontmatter 보존
- 코드 블록 내용 유지 (주석만 번역)

### 3. VERIFICATION-DRIVEN
- 번역 후 구조 검증
- 링크 유효성 확인

## Translation Rules
- AWS 서비스명: 영어 유지 (Amazon SES, AWS Lambda 등)
- 기술 용어: 공식 AWS 한국어 문서 참조
- 이미지 alt 텍스트: 번역
- 코드 주석: 번역
```

---

### 6. Reviewer (품질 검토)

**모델**: `anthropic/claude-sonnet-4-5`

**역할**:
- 번역 품질 검토
- AWS 용어 일관성 확인

**프롬프트 핵심 (Librarian 참고)**:
```
번역 품질 검토 전문가. AWS 공식 문서 기반 용어 검증.

## Tools
- AWS Documentation MCP: 공식 용어 조회
- Context7: 최신 문서 참조

## Review Checklist
- [ ] AWS 서비스명 일관성
- [ ] 기술 용어 정확성
- [ ] 문장 자연스러움
- [ ] Markdown 구조 유지

## Output Format
<review>
<file>/path/to/file.ko.md</file>
<issues>
- Line X: "잘못된 용어" → "올바른 용어"
</issues>
<score>85/100</score>
</review>
```

---

### 7. Validator (구조 검증)

**모델**: `anthropic/claude-haiku-4-5` (빠른 체크)

**역할**:
- Frontmatter 검증
- Markdown 구문 검증
- 파일 완전성 확인

**프롬프트 핵심 (Explore 참고)**:
```
구조 검증 전문가. 번역된 파일의 구조적 정확성 확인.

## Validation Rules
- Frontmatter 필수 필드 (title, weight)
- Markdown 구문 오류 없음
- 모든 .en.md에 대응하는 .{lang}.md 존재

## Output Format
<validation>
<status>PASS/FAIL</status>
<coverage>45/45 files (100%)</coverage>
<errors>
- /path/to/file.ko.md: Missing frontmatter title
</errors>
</validation>
```

---

## MCP 연동

### 1. AWS Documentation MCP
```json
{
  "mcpServers": {
    "aws-docs": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### 2. Context7 MCP
```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@context7/mcp-server"]
    }
  }
}
```

---

## 프로젝트 구조

```
WsTranslator/
├── src/
│   ├── main.py                    # Orchestrator 진입점
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                # 서브에이전트 베이스 클래스
│   │   ├── analyzer.py            # @tool - 구조 분석
│   │   ├── designer.py            # @tool - Design 생성
│   │   ├── task_planner.py        # @tool - Tasks 생성
│   │   ├── translator.py          # @tool - 번역 (병렬)
│   │   ├── reviewer.py            # @tool - 품질 검토
│   │   └── validator.py           # @tool - 구조 검증
│   ├── prompts/
│   │   ├── requirements.md        # 재사용 가능한 요구사항
│   │   ├── system_prompts.py      # 각 에이전트 시스템 프롬프트
│   │   └── templates.py           # Design/Tasks 템플릿
│   ├── tools/
│   │   ├── __init__.py
│   │   └── file_tools.py          # 파일 읽기/쓰기
│   ├── mcp_client/
│   │   └── client.py              # AWS Docs + Context7 MCP
│   └── model/
│       └── load.py                # 다중 모델 로드
├── .bedrock_agentcore.yaml
└── pyproject.toml
```

---

## 사용자 대화 흐름

```
User: 번역 시작

Agent: 안녕하세요! Workshop 번역을 도와드리겠습니다.
       어떤 Workshop 디렉토리를 번역할까요?

User: /path/to/workshop

Agent: 타겟 언어를 선택해주세요. (예: ko, ja, zh)

User: ko

Agent: 분석을 시작합니다...
       [Analyzer 실행]
       
       45개 파일을 발견했습니다.
       Design 문서를 생성합니다...
       [Designer 실행]
       
       Tasks 문서를 생성합니다...
       [TaskPlanner 실행]
       
       번역을 시작합니다... (병렬 처리)
       [Translator 실행 x N]
       
       품질 검토 중...
       [Reviewer 실행]
       
       구조 검증 중...
       [Validator 실행]
       
       ✅ 번역 완료!
       - 번역된 파일: 45개
       - 품질 점수: 92/100
       - 검증 결과: PASS
```

---

## 핵심 구현 포인트

### 1. Agent as Tool 패턴
```python
@tool
def analyze_workshop(workshop_path: str) -> dict:
    """Workshop 구조를 분석하고 번역 대상 파일 목록을 반환합니다."""
    analyzer = Agent(
        model=load_model("haiku"),
        system_prompt=ANALYZER_PROMPT,
        tools=[file_read, glob]
    )
    result = analyzer(f"Analyze workshop at {workshop_path}")
    return parse_analysis_result(result)
```

### 2. 병렬 번역
```python
import asyncio

async def translate_files_parallel(files: list, target_lang: str):
    """여러 파일을 병렬로 번역합니다."""
    tasks = [
        translate_file(file, target_lang) 
        for file in files
    ]
    results = await asyncio.gather(*tasks)
    return results
```

### 3. Todo 추적
```python
def update_task_status(tasks_file: str, task_id: str, status: str):
    """태스크 상태를 업데이트합니다."""
    content = read_file(tasks_file)
    # [ ] → [x] 변환
    updated = content.replace(f"- [ ] {task_id}", f"- [x] {task_id}")
    write_file(tasks_file, updated)
```

---

## 다음 단계

1. `src/agents/` 디렉토리 생성 및 에이전트 구현
2. `src/prompts/` 시스템 프롬프트 작성
3. `src/mcp_client/` MCP 클라이언트 설정
4. `src/main.py` Orchestrator 구현
5. 테스트 및 검증

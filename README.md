# Workshop Translator

AWS Workshop 문서를 자동으로 번역하는 AI Agent 기반 CLI 도구입니다.

## 아키텍처

**Orchestrator 중심 아키텍처**를 사용합니다.

```
┌─────────────────────────────────────────────────────────────────┐
│                      Orchestrator (main.py)                      │
│                    Claude Opus / Sonnet                          │
│                                                                  │
│  핵심 원칙: tasks.md는 오직 Orchestrator만 수정                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │   TaskManager     │
                    │   (싱글톤)         │
                    │                   │
                    │ • 태스크 상태 관리  │
                    │ • 의존성 체크      │
                    │ • tasks.md 동기화  │
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Translator   │    │   Reviewer    │    │   Validator   │
│    Worker     │    │    Worker     │    │    Worker     │
│  (Stateless)  │    │  (Stateless)  │    │  (Stateless)  │
│ 결과만 반환    │    │ 결과만 반환    │    │ 결과만 반환    │
└───────────────┘    └───────────────┘    └───────────────┘
```

### 핵심 설계 원칙

| 항목 | 설명 |
|------|------|
| **중앙 집중식 상태 관리** | tasks.md는 오직 Orchestrator(TaskManager)만 수정 |
| **Stateless Workers** | Sub-agent는 결과만 반환, 상태 파일 직접 수정 안 함 |
| **자동 의존성 관리** | TaskManager가 태스크 간 의존성을 자동으로 체크 |
| **병렬 처리** | ThreadPoolExecutor로 최대 5개 파일 동시 처리 |
| **세션 재개** | 기존 tasks.md 상태를 로드하여 이어서 작업 가능 |

## 디렉토리 구조

```
src/
├── main.py                    # 진입점 (CLI, AgentCore Runtime)
│
├── task_manager/              # 중앙 집중식 태스크 관리
│   ├── types.py               # Task, TaskResult, TaskStatus
│   └── manager.py             # TaskManager 싱글톤
│
├── agents/
│   ├── analyzer.py            # Workshop 구조 분석
│   ├── designer.py            # 설계 문서 생성
│   ├── orchestrator.py        # Orchestrator 도구들
│   └── workers/               # Stateless 워커들
│       ├── translator_worker.py
│       ├── reviewer_worker.py
│       └── validator_worker.py
│
├── mcp_client/                # MCP 클라이언트 (AWS Documentation)
├── model/                     # 모델 로딩 (Opus, Sonnet)
├── prompts/                   # 시스템 프롬프트
└── tools/                     # 파일 읽기/쓰기 도구
```

## 워크플로우

```
Phase 1: 분석/설계
    ├── analyze_workshop()     → Workshop 구조 분석
    └── generate_design()      → 설계 문서 생성
           │
           ▼
Phase 2: 워크플로우 초기화
    └── initialize_workflow()  → TaskManager 초기화, tasks.md 생성
           │
           ▼
Phase 3: 번역
    └── run_translation_phase() → 병렬 번역 실행
           │
           ▼
Phase 4: 검토
    └── run_review_phase()     → 번역 완료 파일만 검토
           │                   → review_report.md 생성
           ▼
Phase 5: 검증
    └── run_validate_phase()   → 번역+검토 완료 파일만 검증
           │                   → validate_report.md 생성
           ▼
Phase 6: 프리뷰
    └── run_preview_phase()    → 로컬 프리뷰 서버 실행
           │                   → http://localhost:8080
           ▼
Phase 7: 완료
    └── get_workflow_status()  → 최종 결과 보고
```

## Orchestrator 도구

| 도구 | 설명 |
|------|------|
| `initialize_workflow` | 워크플로우 초기화, tasks.md 생성 |
| `run_translation_phase` | 번역 단계 병렬 실행 |
| `run_review_phase` | 검토 단계 병렬 실행, review_report.md 생성 |
| `run_validate_phase` | 검증 단계 병렬 실행, validate_report.md 생성 |
| `run_preview_phase` | 로컬 프리뷰 서버 실행 (백그라운드) |
| `stop_preview` | 프리뷰 서버 종료 |
| `get_workflow_status` | 전체 진행 상황 조회 |
| `retry_failed_tasks` | 실패 태스크 재시도 |
| `check_phase_completion` | 단계 완료 여부 확인 |

## 생성되는 파일

번역 작업 시 `translation/` 디렉토리에 다음 파일들이 생성됩니다:

| 파일 | 설명 |
|------|------|
| `tasks.md` | 태스크 진행 상태 (체크박스 형식) |
| `review_report.md` | 검토 단계 리포트 (점수, PASS/FAIL 목록) |
| `validate_report.md` | 검증 단계 리포트 (구조 검증 결과) |

## 설치 및 실행

### PyPI에서 설치 (권장)

```bash
# uvx 사용 (설치 없이 바로 실행)
uvx wstranslator

# 또는 pip으로 설치
pip install wstranslator
wstranslator
```

### 개발 모드 (로컬 개발용)

```bash
# 저장소 클론 후
cd workshop-translator/WsTranslator

# uv 사용
uv sync
uv run wstranslator

# 또는 pip 사용
pip install -e .
wstranslator
```

## 사용 방법

### 대화형 모드

```bash
wstranslator
```

대화형 모드에서 Orchestrator가 자동으로 워크플로우를 진행합니다.

**예시 대화:**
```
사용자: /path/to/workshop 디렉토리를 한국어로 번역해주세요

Orchestrator: Workshop 구조를 분석하겠습니다...
              → 10개 파일 발견
              → 워크플로우 초기화 완료
              → 번역 시작 (5개씩 병렬 처리)
              → 번역 완료: 10/10 (100%)
              → 검토 시작...
              → 검토 완료. review_report.md 생성됨
              → 검증 완료. validate_report.md 생성됨
              → 프리뷰 서버 시작: http://localhost:8080
```

### 세션 재개

이전 세션에서 중단된 작업을 이어서 진행할 수 있습니다:

```
사용자: 이전 번역 작업을 이어서 진행해주세요

Orchestrator: 기존 워크플로우 재개. 25/30 태스크 완료 상태 로드됨.
              → 남은 5개 파일 번역 시작...
```

### 필수 요구사항
- AWS 자격 증명 설정 (AWS CLI 또는 환경 변수)
- Bedrock 모델 접근 권한 (Claude Sonnet)

## 환경 변수

```bash
# AWS 리전 설정 (기본값: us-west-2)
export AWS_REGION=us-west-2

# AWS 프로파일 설정
export AWS_PROFILE=your-profile
```

## 문제 해결

### AWS 자격 증명 오류
```bash
# AWS CLI 설정
aws configure

# 또는 환경 변수 설정
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-west-2
```

### 프리뷰 서버 오류
```bash
# macOS에서 실행 권한 문제 시
# Finder에서 preview_build 파일을 Control-클릭 → 열기

# 파일 열기 제한 오류 시
ulimit -n 10240
```

## 개발자 정보

- **작성자**: Jisan Bang (wltks2155@gmail.com)
- **GitHub**: https://github.com/onesuit/workshop-translator
- **라이선스**: MIT
- **Python 버전**: 3.10+

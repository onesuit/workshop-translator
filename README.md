# Workshop Translator

AWS Workshop 문서를 자동으로 번역하는 AI Agent 기반 CLI 도구입니다.

## 설치

### 방법 1: uv (권장 - 가장 빠름!)

```bash
cd workshop-translator/WsTranslator

# 의존성 설치
uv sync

# 실행!
uv run wstranslator
```

### 방법 2: pip (전통적인 방법)

```bash
# 프로젝트 설치
pip install -e .

# 실행!
wstranslator
```

### 방법 3: PyPI에서 설치 (배포 후)

```bash
# uv 사용
uvx wstranslator

# 또는 pip 사용
pip install wstranslator
wstranslator
```

## 사용 방법

### 로컬 모드 (권장)

로컬에서 직접 Bedrock을 호출하여 실행합니다. AgentCore 설정이 필요 없습니다.

#### 필수 요구사항
- AWS 자격 증명 설정 (AWS CLI 또는 환경 변수)
- Bedrock 모델 접근 권한

#### 대화형 모드
```bash
# uv 사용
uv run wstranslator

# 또는 pip 설치 후
wstranslator
```

대화형 모드에서는 여러 질문을 연속으로 할 수 있으며, 종료하려면 `exit` 또는 `quit`를 입력하세요.

#### 단일 쿼리
```bash
uv run wstranslator "워크샵 분석"
# 또는
wstranslator "워크샵 분석"
```

### 원격 모드 (고급)

이미 배포된 AgentCore Runtime을 사용하여 실행합니다. 
원격 모드를 사용하려면 별도의 AgentCore Runtime 배포와 IAM 권한 설정이 필요합니다.

#### AgentCore Runtime 배포

1. `.bedrock_agentcore.yaml` 파일 준비
2. AgentCore CLI로 배포:
   ```bash
   agentcore deploy
   ```
3. Runtime ARN 확인

#### 원격 모드 실행

원격 모드 코드는 `src/cli_remote_backup.py`에 백업되어 있습니다.
필요한 경우 해당 파일을 참고하여 구현할 수 있습니다.

## 옵션

```
wstranslator [PROMPT]

인자:
  PROMPT              번역 요청 또는 질문 (선택사항, 없으면 대화형 모드)

환경 변수:
  AWS_REGION          AWS 리전 (기본값: us-east-1)
  AWS_PROFILE         AWS 프로파일
```

## 문제 해결

### AWS 자격 증명 오류
```bash
# AWS CLI 설정
aws configure

# 또는 환경 변수 설정
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1
```

### Bedrock 모델 접근 권한 오류
AWS 콘솔에서 Bedrock 모델 접근 권한을 활성화해야 합니다:
1. AWS Console > Bedrock > Model access
2. 필요한 모델 활성화 (예: Claude 3.5 Sonnet)

### 의존성 설치 문제
```bash
# uv 사용 시
uv sync

# pip 사용 시
pip install -e .
```

## 개발자 정보

- **작성자**: Jisan Bang (wltks2155@gmail.com)
- **GitHub**: https://github.com/onesuit/workshop-translator
- **라이선스**: MIT
- **Python 버전**: 3.10+

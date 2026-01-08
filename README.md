# Workshop Translator

AWS Workshop 문서를 자동으로 번역하는 AI Agent 기반 CLI 도구입니다.

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
# uvx 사용 (가장 간단!)
uvx wstranslator

# 또는 설치 후
wstranslator
```

대화형 모드에서는 여러 질문을 연속으로 할 수 있으며, 종료하려면 `exit` 또는 `quit`를 입력하세요.

### 필수 요구사항
- AWS 자격 증명 설정 (AWS CLI 또는 환경 변수)
- Bedrock 모델 접근 권한 (기본적으로 활성화됨)

<!--
### 원격 모드 (고급)

이미 배포된 AgentCore Runtime을 사용하여 실행합니다. 
원격 모드를 사용하려면 별도의 AgentCore Runtime 배포와 IAM 권한 설정이 필요합니다.

#### AgentCore Runtime 배포

1. `.bedrock_agentcore.yaml` 파일 준비
2. AgentCore CLI로 설정:
   ```bash
   agentcore configure --name YourAgentName
   ```
3. AgentCore CLI로 배포:
   ```bash
   agentcore deploy
   ```
4. Runtime ARN 확인

#### 원격 모드 실행

원격 모드 코드는 `src/cli_remote_backup.py`에 백업되어 있습니다.
필요한 경우 해당 파일을 참고하여 구현할 수 있습니다.
-->

## 환경 변수

```bash
# AWS 리전 설정 (기본값: us-east-1)
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
export AWS_REGION=us-east-1
```

## 개발자 정보

- **작성자**: Jisan Bang (wltks2155@gmail.com)
- **GitHub**: https://github.com/onesuit/workshop-translator
- **라이선스**: MIT
- **Python 버전**: 3.10+

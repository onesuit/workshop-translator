# MCP 통합 작업 ToDo

## 개요
Workshop Translator의 Translator 에이전트에서 MCP 도구를 활용하여 AWS 문서 및 라이브러리 문서를 참조할 수 있도록 합니다.

## 결정 사항
- **MCP 통신 방식**: Runtime 내부에서 stdio로 MCP 서버 subprocess 실행
- **사용 패키지**: `mcp` 패키지 (Strands Agent 공식 문서 권장)
- **적용 대상**: Translator 에이전트

---

## ToDo 목록

### 1. MCP 클라이언트 구현 (`mcp_client/client.py` 수정)

#### 1.1 stdio MCP 클라이언트 추가
```python
from mcp import stdio_client, StdioServerParameters
from strands.tools.mcp import MCPClient

# AWS Documentation MCP Server
aws_docs_mcp_client = MCPClient(
    lambda: stdio_client(
        StdioServerParameters(
            command="uvx",
            args=["awslabs.aws-documentation-mcp-server@latest"],
            env={"AWS_DOCUMENTATION_PARTITION": "aws"}
        )
    ),
    prefix="aws_docs"  # 도구 이름 충돌 방지
)

# Context7 MCP Server
context7_mcp_client = MCPClient(
    lambda: stdio_client(
        StdioServerParameters(
            command="npx",
            args=["-y", "@context7/mcp-server"]
        )
    ),
    prefix="context7"
)
```

#### 1.2 구현 시 고려사항
- [ ] Context Manager 사용 필수 (`with` 문)
- [ ] 여러 MCP 서버 동시 사용 시 도구 이름 prefix 적용
- [ ] 타임아웃 설정 (기본 30초)
- [ ] 에러 핸들링 (MCPClientInitializationError)

---

### 2. Translator 에이전트 수정 (`agents/translator.py`)

#### 2.1 MCP 도구 통합
```python
from mcp_client.client import aws_docs_mcp_client, context7_mcp_client

# Translator 에이전트에서 MCP 도구 사용
with aws_docs_mcp_client, context7_mcp_client:
    tools = (
        aws_docs_mcp_client.list_tools_sync() + 
        context7_mcp_client.list_tools_sync()
    )
    
    translator_agent = Agent(
        model=load_sonnet(),
        system_prompt=TRANSLATOR_PROMPT,
        tools=[
            file_read,
            file_write,
            *tools  # MCP 도구 추가
        ]
    )
```

#### 2.2 활용 시나리오
- AWS 서비스 관련 용어 번역 시 공식 문서 참조
- 기술 용어의 정확한 한국어 번역 확인
- 라이브러리/프레임워크 문서 참조 (Context7)

---

### 3. 시스템 프롬프트 업데이트 (`prompts/system_prompts.py`)

#### 3.1 Translator 프롬프트에 MCP 도구 사용 지침 추가
- [ ] AWS 문서 검색 도구 사용 시점 명시
- [ ] Context7 도구 사용 시점 명시
- [ ] 도구 결과 활용 방법 안내

---

### 4. 의존성 확인

#### 4.1 requirements.txt 업데이트
```
mcp>=1.0.0
strands-agents>=0.1.0
```

#### 4.2 Runtime 환경 확인
- [ ] `uvx` 명령어 사용 가능 여부 (uv 패키지 매니저)
- [ ] `npx` 명령어 사용 가능 여부 (Node.js)
- [ ] AgentCore Runtime에서 subprocess 실행 가능 여부

---

### 5. 테스트

#### 5.1 로컬 테스트
- [ ] AWS Documentation MCP 서버 연결 테스트
- [ ] Context7 MCP 서버 연결 테스트
- [ ] Translator 에이전트에서 MCP 도구 호출 테스트

#### 5.2 Runtime 배포 후 테스트
- [ ] AgentCore Runtime에서 MCP 서버 실행 확인
- [ ] 도구 호출 응답 시간 측정
- [ ] 에러 핸들링 동작 확인

---

## 참고 자료

### Strands Agent MCP 문서
- https://strandsagents.com/latest/documentation/docs/user-guide/concepts/tools/mcp-tools/

### MCP 서버 정보
- AWS Documentation: `uvx awslabs.aws-documentation-mcp-server@latest`
- Context7: `npx -y @context7/mcp-server`

### 주요 코드 패턴
```python
# 기본 사용법 (Context Manager 필수)
from mcp import stdio_client, StdioServerParameters
from strands import Agent
from strands.tools.mcp import MCPClient

mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(
        command="uvx",
        args=["awslabs.aws-documentation-mcp-server@latest"]
    )
))

with mcp_client:
    tools = mcp_client.list_tools_sync()
    agent = Agent(tools=tools)
    agent("What is AWS Lambda?")
```

### 여러 MCP 서버 사용
```python
with sse_mcp_client, stdio_mcp_client:
    tools = sse_mcp_client.list_tools_sync() + stdio_mcp_client.list_tools_sync()
    agent = Agent(tools=tools)
```

---

## 우선순위
1. ⬜ Runtime 배포 및 기본 동작 테스트 (현재 진행 중)
2. ⬜ MCP 클라이언트 구현
3. ⬜ Translator 에이전트 통합
4. ⬜ 시스템 프롬프트 업데이트
5. ⬜ 전체 테스트

---

## 관련 파일
- `workshop-translator/WsTranslator/src/mcp_client/client.py`
- `workshop-translator/WsTranslator/src/agents/translator.py`
- `workshop-translator/WsTranslator/src/prompts/system_prompts.py`
- `workshop-translator/WsTranslator/src/main.py`

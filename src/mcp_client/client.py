# MCP 클라이언트 설정
# AWS Documentation MCP + Context7 연동

from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient
from typing import Optional

# MCP 서버 엔드포인트 설정
# 참고: 실제 배포 시 환경 변수로 설정 권장
MCP_ENDPOINTS = {
    # AWS Documentation MCP Server
    # uvx awslabs.aws-documentation-mcp-server@latest 로 로컬 실행 필요
    "aws_docs": None,  # 로컬 실행 시 별도 설정 필요
    
    # Context7 MCP Server  
    # npx -y @context7/mcp-server 로 로컬 실행 필요
    "context7": None,  # 로컬 실행 시 별도 설정 필요
    
    # Exa AI (예시용)
    "exa": "https://mcp.exa.ai/mcp",
}


def get_streamable_http_mcp_client(
    endpoint: str = None,
    access_token: Optional[str] = None
) -> MCPClient:
    """
    Streamable HTTP MCP 클라이언트를 반환합니다.
    
    Args:
        endpoint: MCP 서버 엔드포인트 URL
        access_token: Bearer 인증 토큰 (선택)
    
    Returns:
        MCPClient: Strands 호환 MCP 클라이언트
    """
    if endpoint is None:
        endpoint = MCP_ENDPOINTS.get("exa", "https://mcp.exa.ai/mcp")
    
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    
    if headers:
        return MCPClient(lambda: streamablehttp_client(endpoint, headers=headers))
    else:
        return MCPClient(lambda: streamablehttp_client(endpoint))


# MCP 설정 파일 템플릿 (참고용)
MCP_CONFIG_TEMPLATE = """
{
  "mcpServers": {
    "aws-docs": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@context7/mcp-server"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
"""


def get_mcp_config_path() -> str:
    """
    MCP 설정 파일 경로를 반환합니다.
    
    Returns:
        str: mcp.json 파일 경로
    """
    import os
    
    # 워크스페이스 레벨 설정
    workspace_config = ".kiro/settings/mcp.json"
    if os.path.exists(workspace_config):
        return workspace_config
    
    # 사용자 레벨 설정
    user_config = os.path.expanduser("~/.kiro/settings/mcp.json")
    if os.path.exists(user_config):
        return user_config
    
    return workspace_config


def create_mcp_config():
    """
    MCP 설정 파일을 생성합니다.
    """
    import os
    import json
    
    config_path = get_mcp_config_path()
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    config = {
        "mcpServers": {
            "aws-docs": {
                "command": "uvx",
                "args": ["awslabs.aws-documentation-mcp-server@latest"],
                "env": {
                    "FASTMCP_LOG_LEVEL": "ERROR"
                },
                "disabled": False,
                "autoApprove": []
            },
            "context7": {
                "command": "npx",
                "args": ["-y", "@context7/mcp-server"],
                "disabled": False,
                "autoApprove": []
            }
        }
    }
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    return config_path

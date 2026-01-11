# MCP 클라이언트 설정
# AWS Documentation MCP 연동 (stdio 방식)

import os
from typing import Optional, List
from contextlib import contextmanager

from mcp import stdio_client, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient


class AWSDocsMCPClient:
    """
    AWS Documentation MCP 클라이언트
    
    uvx awslabs.aws-documentation-mcp-server@latest 를 사용하여
    AWS 공식 문서를 검색하고 읽을 수 있습니다.
    
    사용 예시:
        with AWSDocsMCPClient() as client:
            tools = client.list_tools()
            # Agent에서 tools 사용
    """
    
    def __init__(self, log_level: str = "ERROR"):
        """
        Args:
            log_level: FastMCP 로그 레벨 (ERROR, WARNING, INFO, DEBUG)
        """
        self._log_level = log_level
        self._client: Optional[MCPClient] = None
    
    def _create_client(self) -> MCPClient:
        """MCP 클라이언트 생성"""
        return MCPClient(
            lambda: stdio_client(
                StdioServerParameters(
                    command="uvx",
                    args=["awslabs.aws-documentation-mcp-server@latest"],
                    env={"FASTMCP_LOG_LEVEL": self._log_level}
                )
            ),
            # 필요한 도구만 필터링
            tool_filters={
                "allowed": ["search_documentation", "read_documentation"]
            }
        )
    
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        self._client = self._create_client()
        self._client.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        if self._client:
            self._client.__exit__(exc_type, exc_val, exc_tb)
            self._client = None
    
    def list_tools(self) -> List:
        """사용 가능한 도구 목록 반환"""
        if not self._client:
            raise RuntimeError("MCP 클라이언트가 초기화되지 않았습니다. 'with' 문 안에서 사용하세요.")
        return self._client.list_tools_sync()
    
    def search_documentation(self, query: str) -> dict:
        """
        AWS 문서 검색
        
        Args:
            query: 검색어 (예: "Amazon SES configuration set")
        
        Returns:
            dict: 검색 결과
        """
        if not self._client:
            raise RuntimeError("MCP 클라이언트가 초기화되지 않았습니다.")
        
        return self._client.call_tool_sync(
            tool_use_id="search-doc",
            name="search_documentation",
            arguments={"query": query}
        )
    
    def read_documentation(self, url: str) -> dict:
        """
        AWS 문서 읽기
        
        Args:
            url: AWS 문서 URL
        
        Returns:
            dict: 문서 내용
        """
        if not self._client:
            raise RuntimeError("MCP 클라이언트가 초기화되지 않았습니다.")
        
        return self._client.call_tool_sync(
            tool_use_id="read-doc",
            name="read_documentation",
            arguments={"url": url}
        )


@contextmanager
def get_aws_docs_client(log_level: str = "ERROR"):
    """
    AWS Documentation MCP 클라이언트를 컨텍스트 매니저로 반환
    
    사용 예시:
        with get_aws_docs_client() as client:
            tools = client.list_tools()
    """
    client = AWSDocsMCPClient(log_level=log_level)
    with client:
        yield client


def get_aws_docs_tools(log_level: str = "ERROR") -> tuple:
    """
    AWS Documentation MCP 도구와 클라이언트를 반환
    
    주의: 반환된 클라이언트는 컨텍스트 매니저로 관리해야 합니다.
    
    Returns:
        tuple: (MCPClient, tools_list)
    """
    client = MCPClient(
        lambda: stdio_client(
            StdioServerParameters(
                command="uvx",
                args=["awslabs.aws-documentation-mcp-server@latest"],
                env={"FASTMCP_LOG_LEVEL": log_level}
            )
        ),
        tool_filters={
            "allowed": ["search_documentation", "read_documentation"]
        }
    )
    return client


# 기존 HTTP 기반 클라이언트 (하위 호환성 유지)
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
        endpoint = "https://mcp.exa.ai/mcp"
    
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    
    if headers:
        return MCPClient(lambda: streamablehttp_client(endpoint, headers=headers))
    else:
        return MCPClient(lambda: streamablehttp_client(endpoint))

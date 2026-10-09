"""麦麦精算师 — 麦当劳 MCP Streamable HTTP 客户端（仅标准库，无第三方依赖）。

仅在使用真实 MCP Token 时启用（CLI 的 --live 模式 / WorkBuddy 连接器）。
dry-run 模式不调用本模块，使用 src/mock_data.py 演示算法。

协议要点：
  - 传输：Streamable HTTP，POST JSON-RPC 到 https://mcp.mcd.cn
  - 鉴权：请求头 Authorization: Bearer <MCD_MCP_TOKEN>
  - 兼容：遵循 MCP 2025-06-18（麦当劳 MCP Server 支持的最高版本）
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

DEFAULT_URL = "https://mcp.mcd.cn"


class McdMCPError(RuntimeError):
    """MCP 调用相关错误。"""


class McdMCP:
    def __init__(self, token: str, url: str = DEFAULT_URL):
        self.token = token
        self.url = url
        self.session_id = None
        self._id = 0

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def _post(self, method: str, params: dict = None) -> dict:
        payload = {"jsonrpc": "2.0", "id": self._next_id(), "method": method}
        if params is not None:
            payload["params"] = params
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        req.add_header("Authorization", f"Bearer {self.token}")
        if self.session_id:
            req.add_header("Mcp-Session-Id", self.session_id)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if "Mcp-Session-Id" in resp.headers:
                    self.session_id = resp.headers["Mcp-Session-Id"]
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raise McdMCPError(
                f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}"
            ) from e
        return self._parse(body)

    @staticmethod
    def _parse(body: str) -> dict:
        body = body.strip()
        if body.startswith("event:") or "data:" in body:
            last = None
            for line in body.splitlines():
                if line.startswith("data:"):
                    last = line[5:].strip()
            if not last:
                raise McdMCPError("无法解析 SSE 响应")
            return json.loads(last)
        return json.loads(body)

    def initialize(self) -> dict:
        return self._post(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "mcd-smart-order-optimizer", "version": "1.0.0"},
            },
        )

    def list_tools(self) -> list:
        return self._post("tools/list").get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict) -> dict:
        return self._post("tools/call", {"name": name, "arguments": arguments}).get(
            "result", {}
        )

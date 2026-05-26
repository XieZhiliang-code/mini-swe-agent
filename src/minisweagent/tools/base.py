"""Base types for tools."""

from typing import Any, Protocol

ToolResult = dict[str, Any]


class Tool(Protocol):
    """Protocol for tools that execute model actions."""

    name: str

    def run(self, action: dict[str, Any]) -> ToolResult: ...

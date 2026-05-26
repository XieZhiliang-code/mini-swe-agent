"""Tool runner that dispatches model actions to concrete tools."""

from typing import Any

from minisweagent.tools.base import Tool, ToolResult
from minisweagent.tools.bash import BashTool


class ToolRunner:
    def __init__(self, tools: list[Tool] | None = None):
        tools = tools or []
        self.tools = {tool.name: tool for tool in tools}

    @classmethod
    def for_environment(cls, env) -> "ToolRunner":
        return cls([BashTool(env)])

    def run(self, actions: list[dict[str, Any]]) -> list[ToolResult]:
        return [self.run_action(action) for action in actions]

    def run_action(self, action: dict[str, Any]) -> ToolResult:
        tool_name = action.get("tool") or action.get("name") or BashTool.name
        tool = self.tools.get(tool_name)
        if tool is None:
            return {
                "output": "",
                "returncode": -1,
                "exception_info": f"Unknown tool: {tool_name}",
                "extra": {"exception_type": "UnknownTool", "tool_name": tool_name},
            }
        return tool.run(action)

"""Bash tool backed by the existing environment execution API."""

from typing import Any

from minisweagent import Environment
from minisweagent.tools.base import ToolResult


class BashTool:
    name = "bash"

    def __init__(self, env: Environment):
        self.env = env

    def run(self, action: dict[str, Any]) -> ToolResult:
        return self.env.execute(action)

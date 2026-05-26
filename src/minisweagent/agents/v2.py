"""V2 agent skeleton with a separate tool execution layer."""

from minisweagent.agents.default import AgentConfig, DefaultAgent
from minisweagent.tools import ToolRunner


class V2Agent(DefaultAgent):
    """DefaultAgent-compatible skeleton that routes actions through ToolRunner."""

    def __init__(self, *args, tool_runner: ToolRunner | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tool_runner = tool_runner or ToolRunner.for_environment(self.env)

    def execute_actions(self, message: dict) -> list[dict]:
        """Execute actions through the tool runner, add observation messages, return them."""
        outputs = self.tool_runner.run(message.get("extra", {}).get("actions", []))
        return self.add_messages(*self.model.format_observation_messages(message, outputs, self.get_template_vars()))


__all__ = ["AgentConfig", "V2Agent"]

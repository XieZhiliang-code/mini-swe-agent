from minisweagent.agents.v2 import V2Agent
from minisweagent.environments.local import LocalEnvironment
from minisweagent.models.test_models import DeterministicModel, make_output


def test_v2_executes_bash_action_and_adds_observation():
    agent = V2Agent(
        model=DeterministicModel(outputs=[make_output("Run command", [{"command": "printf v2-smoke"}])]),
        env=LocalEnvironment(),
        system_template="system",
        instance_template="task: {{task}}",
    )

    agent.add_messages({"role": "system", "content": "system"}, {"role": "user", "content": "task"})
    messages = agent.step()

    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert "<returncode>0</returncode>" in messages[0]["content"]
    assert "v2-smoke" in messages[0]["content"]

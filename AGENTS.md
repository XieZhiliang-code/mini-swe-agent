# Agent Notes for mini-swe-agent-v2

This worktree is the v2 evolution branch for the local `mini-swe-agent` work.
It is intended to stay separate from `/mnt/d/111OnlyAgentWork/mini-swe-agent`
so future agents can compare the original baseline against the v2 skeleton.

## Repository Role

- Current worktree: `/mnt/d/111OnlyAgentWork/mini-swe-agent-v2`
- Branch: `agent-v2`
- Source baseline: committed `HEAD` from `/mnt/d/111OnlyAgentWork/mini-swe-agent`
- Purpose: evolve the local mini-swe-agent into a more structured agent runtime while preserving baseline behavior.

Do not assume uncommitted changes from the original `mini-swe-agent` directory exist here.
This v2 worktree intentionally started from committed baseline code only.

## Current V2 Shape

The first v2 step is deliberately small:

- `minisweagent.agents.v2.V2Agent` inherits the existing `DefaultAgent`.
- It reuses the baseline query, save, template rendering, message history, and limit logic.
- Only action execution is split out through `ToolRunner`.
- The only concrete tool currently available is `BashTool`, which delegates to the existing `env.execute(action)` path.

Important files:

- `src/minisweagent/agents/v2.py`
- `src/minisweagent/tools/base.py`
- `src/minisweagent/tools/bash.py`
- `src/minisweagent/tools/runner.py`
- `src/minisweagent/config/mini_v2.yaml`
- `tests/agents/test_v2.py`

## How to Run

Baseline command from the original style:

```bash
mini -c mini.yaml -t "print hello with a command"
```

V2 command from this worktree:

```bash
cd /mnt/d/111OnlyAgentWork/mini-swe-agent-v2
mini -c mini_v2.yaml -t "print hello with a command"
```

For deterministic local smoke tests without a real model:

```bash
UV_CACHE_DIR=.uv-cache uv run mini \
  -c mini_v2.yaml \
  -c 'model.model_class=deterministic' \
  -c 'model.model_name=deterministic' \
  -c 'model.outputs=[{"role":"assistant","content":"Run command","extra":{"actions":[{"command":"echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\necho cli-v2-smoke"}],"cost":0.0}}]' \
  -t "print hello with a command" \
  --exit-immediately \
  -o output/v2_cli_smoke.traj.json
```

Use a repo-local uv cache because global cache permissions may fail in this environment:

```bash
UV_CACHE_DIR=.uv-cache uv run ...
```

## Development Workflow

When changing this v2 runtime, preserve this order:

1. Keep baseline behavior passing.
2. Add or adjust a narrow v2 abstraction.
3. Add focused tests for the abstraction.
4. Run the focused tests.
5. Run the broader baseline regression set.
6. Do a CLI smoke through `mini_v2.yaml` when config or agent wiring changes.

Recommended verification commands:

```bash
UV_CACHE_DIR=.uv-cache uv run pytest tests/agents/test_init.py tests/agents/test_v2.py
UV_CACHE_DIR=.uv-cache uv run pytest tests/agents tests/models/test_actions_toolcall.py tests/run/test_run_hello_world.py
UV_CACHE_DIR=.uv-cache uv run --extra dev ruff check src/minisweagent/agents src/minisweagent/tools tests/agents
```

## Architecture Direction

Treat `V2Agent` as a migration layer, not a rewrite.
The first priority is a runnable skeleton that behaves like the baseline.

Good next steps:

- Add typed tools one at a time.
- Keep bash behavior compatible with the current model action format.
- Add read-only tools before edit tools.
- Add parallel execution only for clearly read-only tools.
- Add context budget and summarization only after tool behavior is stable.
- Add a verification pass after execution is well factored.

Avoid doing these too early:

- Do not copy a large external Claude Code-style implementation into this repo.
- Do not replace `DefaultAgent` logic unless the replacement is covered by tests.
- Do not add read/edit/grep/glob/todo/verifier all at once.
- Do not break `mini -c mini.yaml ...`; baseline behavior remains the comparison target.

## Agent Handoff Rules

For future agents working here:

- Start by reading this file, `src/minisweagent/agents/default.py`, and `src/minisweagent/agents/v2.py`.
- Check `git status --short --branch` before editing.
- Treat uncommitted user changes as intentional; do not revert them unless explicitly asked.
- Keep changes scoped to v2 runtime files unless the task requires broader wiring.
- If adding a tool, put execution logic under `src/minisweagent/tools/` and test it through `V2Agent` or `ToolRunner`.
- If changing config behavior, test through `mini_v2.yaml`.
- If changing shared model/env behavior, also run the baseline regression set above.

The design goal is incremental replacement: each step should make the runtime easier to extend while keeping the current mini-swe-agent behavior easy to compare.

# mini-swe-agent v2 Skeleton

This branch is a local evolution of the upstream
[`SWE-agent/mini-swe-agent`](https://github.com/SWE-agent/mini-swe-agent)
project. The goal is to keep the original agent behavior runnable while
incrementally refactoring the runtime toward a more extensible tool-based
architecture.

For the preserved upstream README, see [README.upstream.md](README.upstream.md).
For future-agent handoff notes, see [AGENTS.md](AGENTS.md).

## What This Branch Adds

The first v2 milestone is intentionally small and testable:

1. `V2Agent`
   - New agent class: `src/minisweagent/agents/v2.py`
   - Inherits the existing `DefaultAgent`
   - Reuses baseline query, message history, templates, save logic, and limits
   - Refactors only action execution through a tool runner

2. Minimal tool runtime
   - New package: `src/minisweagent/tools/`
   - Defines a small `Tool` / `ToolResult` abstraction
   - Adds `BashTool`, backed by the existing `env.execute(action)` behavior
   - Adds `ToolRunner`, which dispatches model actions to tools

3. Config and registration
   - Registers `agent_class: v2`
   - Adds `src/minisweagent/config/mini_v2.yaml`
   - Keeps the existing `mini.yaml` baseline unchanged

4. Tests
   - Verifies `get_agent_class("v2")`
   - Adds a `V2Agent` smoke test that executes a bash action and records an observation
   - Runs baseline agent/tool-call tests to guard compatibility

## Why This Matters

The upstream mini-swe-agent implementation is intentionally compact. That makes
it easy to understand, but harder to extend with a richer tool system.

This branch starts an incremental migration path:

- preserve the working baseline;
- isolate tool execution behind a small interface;
- keep each step runnable and covered by tests;
- prepare for typed tools, read-only parallelism, context budgeting, and a later verification pass.

This is not a wholesale rewrite. It is a compatibility-preserving skeleton for
future agent runtime work.

## Repository Layout

Key files for this branch:

```text
src/minisweagent/agents/v2.py          # V2Agent skeleton
src/minisweagent/tools/base.py         # Tool protocol and ToolResult type
src/minisweagent/tools/bash.py         # BashTool adapter over env.execute()
src/minisweagent/tools/runner.py       # ToolRunner dispatcher
src/minisweagent/config/mini_v2.yaml   # V2 mini config
tests/agents/test_v2.py                # V2 smoke test
AGENTS.md                             # Handoff notes for future agents
```

## Running It

Baseline mini-swe-agent behavior still uses:

```bash
mini -c mini.yaml -t "print hello with a command"
```

The v2 skeleton uses:

```bash
mini -c mini_v2.yaml -t "print hello with a command"
```

When running from a fresh local checkout with `uv`:

```bash
UV_CACHE_DIR=.uv-cache uv run mini -c mini_v2.yaml -t "print hello with a command"
```

Deterministic smoke test without a real model:

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

## Verification

The v2 branch was verified with:

```bash
UV_CACHE_DIR=.uv-cache uv run pytest tests/agents/test_init.py tests/agents/test_v2.py
UV_CACHE_DIR=.uv-cache uv run pytest tests/agents tests/models/test_actions_toolcall.py tests/run/test_run_hello_world.py
UV_CACHE_DIR=.uv-cache uv run --extra dev ruff check src/minisweagent/agents src/minisweagent/tools tests/agents
```

Expected results at this milestone:

```text
12 focused tests passed
182 baseline regression tests passed
ruff checks passed
```

## Next Milestones

Planned direction:

1. Add typed read-only tools, such as file read, grep, and glob.
2. Keep bash compatibility with the existing model action format.
3. Add parallel execution only for clearly read-only tools.
4. Add edit tools with focused tests and conservative failure behavior.
5. Add context budget handling after tool behavior is stable.
6. Add a verification pass after execution is well factored.

## Notes

This branch is designed to be reviewed as an engineering artifact: a small,
tested migration step from a minimal baseline agent toward a more extensible
agent runtime.

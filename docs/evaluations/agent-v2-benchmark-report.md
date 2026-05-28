# Agent V2 Benchmark Report

Date: 2026-05-28

This report summarizes the current A/B evaluation of the original
`mini-swe-agent`-style baseline agent against the local `agent-v2` structured
tool runtime. The goal is to measure whether the Claude Code-inspired v2
runtime improves benchmark performance, not just whether the architecture is
cleaner.

## Executive Summary

The current v2 runtime is not yet a benchmark win overall.

| Benchmark | Baseline Agent | V2 Agent | Delta |
| --- | ---: | ---: | ---: |
| Terminal-Bench 2.1, 89 tasks | 56/89, 62.9% | 54/89, 60.7% | -2 |
| SWE-bench Pro, 30 tasks | 16/30, 53.3% | 15/30, 50.0% | -1 |

The result is still useful: v2 solves tasks the baseline misses, but it also
regresses a larger number of baseline-solved tasks. The next work should focus
on regression analysis and tool-policy tuning, not another broad rewrite.

## Agent Variants

Baseline agent:

- Original bash-first `mini-swe-agent` runtime.
- Uses the same model, task set, Docker setup, and budget as v2 in each A/B.
- Serves as the preserved comparison target.

V2 agent:

- `V2Agent` routes model actions through a structured `ToolRunner`.
- Adds structured tools: `read_file`, `grep`, `glob`, and `edit_file`.
- Keeps `bash` as the fallback execution tool.
- Uses registry-generated tool schemas for model tool calls.
- Preserves baseline runtime behavior where possible.

## Terminal-Bench 2.1

Configuration:

- Dataset: local Terminal-Bench 2.1 task set, 89 tasks.
- Docker images: all 89 task images pre-pulled locally.
- Model: `deepseek/deepseek-v4-pro`.
- API key handling: `DEEPSEEK_API_KEY` from environment only.
- Workers: 6.
- Agent step limit: 80.
- Command timeout: 120 seconds.
- Container timeout: 2 hours.
- Runner: `scripts/run_terminal_bench.py`.

Commands:

```bash
UV_CACHE_DIR=.uv-cache uv run python scripts/run_terminal_bench.py \
  --tasks-dir /mnt/d/111OnlyAgentWork/terminal-bench-2-1/terminal-bench-2-1 \
  -c mini.yaml \
  -c model.cost_tracking=ignore_errors \
  -o output/tbench21_89_baseline_deepseek_v4_pro_w6_step80 \
  --workers 6 \
  --model deepseek/deepseek-v4-pro \
  --api-base https://api.deepseek.com \
  --step-limit 80 \
  --command-timeout 120 \
  --container-timeout 2h
```

```bash
UV_CACHE_DIR=.uv-cache uv run python scripts/run_terminal_bench.py \
  --tasks-dir /mnt/d/111OnlyAgentWork/terminal-bench-2-1/terminal-bench-2-1 \
  -c mini_v2.yaml \
  -c model.cost_tracking=ignore_errors \
  -o output/tbench21_89_v2_deepseek_v4_pro_w6_step80 \
  --workers 6 \
  --model deepseek/deepseek-v4-pro \
  --api-base https://api.deepseek.com \
  --step-limit 80 \
  --command-timeout 120 \
  --container-timeout 2h
```

Results:

| Metric | Baseline Agent | V2 Agent |
| --- | ---: | ---: |
| Passed | 56 | 54 |
| Total | 89 | 89 |
| Pass rate | 62.9% | 60.7% |
| Total model calls | 3182 | 3151 |
| Both passed | 46 | 46 |
| Both failed | 25 | 25 |
| V2-only passes | 0 | 8 |
| Baseline-only passes | 10 | 0 |

### V2 Gains

These tasks failed with the baseline and passed with v2.

| Task | Baseline | V2 | Baseline calls | V2 calls | Baseline status | V2 status |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `adaptive-rejection-sampler` | 0 | 1 | 40 | 49 | Submitted | Submitted |
| `circuit-fibsqrt` | 0 | 1 | 80 | 52 | LimitsExceeded | Submitted |
| `filter-js-from-html` | 0 | 1 | 40 | 37 | Submitted | Submitted |
| `mteb-leaderboard` | 0 | 1 | 80 | 77 | LimitsExceeded | Submitted |
| `pytorch-model-cli` | 0 | 1 | 56 | 23 | Submitted | Submitted |
| `qemu-startup` | 0 | 1 | 80 | 24 | LimitsExceeded | Submitted |
| `regex-log` | 0 | 1 | 21 | 18 | Submitted | Submitted |
| `sqlite-with-gcov` | 0 | 1 | 29 | 38 | Submitted | Submitted |

### V2 Regressions

These tasks passed with the baseline and failed with v2.

| Task | Baseline | V2 | Baseline calls | V2 calls | Baseline status | V2 status |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `configure-git-webserver` | 1 | 0 | 32 | 20 | Submitted | Submitted |
| `mailman` | 1 | 0 | 27 | 45 | Submitted | Submitted |
| `merge-diff-arc-agi-task` | 1 | 0 | 22 | 19 | Submitted | Submitted |
| `qemu-alpine-ssh` | 1 | 0 | 48 | 80 | Submitted | LimitsExceeded |
| `reshard-c4-data` | 1 | 0 | 37 | 32 | Submitted | Submitted |
| `rstan-to-pystan` | 1 | 0 | 80 | 80 | LimitsExceeded | LimitsExceeded |
| `sam-cell-seg` | 1 | 0 | 68 | 49 | Submitted | Submitted |
| `sqlite-db-truncate` | 1 | 0 | 11 | 9 | Submitted | Submitted |
| `tune-mjcf` | 1 | 0 | 10 | 23 | Submitted | Submitted |
| `winning-avg-corewars` | 1 | 0 | 66 | 80 | Submitted | LimitsExceeded |

Interpretation:

- V2 improves several tasks that benefit from more disciplined exploration or
  exact file/tool use.
- V2 regresses tasks where the baseline's direct shell workflow is probably
  better aligned with Terminal-Bench's terminal-centric task format.
- The structured-tool layer is useful, but the current policy exposes it too
  broadly for tasks that are not source-code patch workflows.

## SWE-bench Pro

Configuration:

- Dataset: local 30-task SWE-bench Pro set.
- Model: DeepSeek V4 Pro.
- Baseline worktree: local original `mini-swe-agent`.
- V2 config: `src/minisweagent/config/benchmarks/swebench_pro_v2.yaml`.
- V2 output: `output/deepseek_v4_pro_swebench_pro30_v2_structured_w10_step300`.
- V2 eval summary:
  `logs/swebench_pro/deepseek_v4_pro_swebench_pro30_v2_structured_w10_step300_eval/summary.json`.

Results:

| Slice | Baseline Agent | V2 Agent |
| --- | ---: | ---: |
| Rows 0-9 | 4/10 | 5/10 |
| Rows 10-29 | 12/20 | 10/20 |
| Total | 16/30 | 15/30 |

Interpretation:

- V2 improved 3 instances the baseline missed.
- V2 lost 4 instances the baseline solved.
- Net result: -1 task.
- The evidence again points to targeted regression repair instead of more
  architecture churn.

## Main Takeaways

1. The v2 runtime is credible engineering infrastructure, but not yet a net
   benchmark improvement.
2. Structured tools do create real wins, especially on tasks where bounded
   reading, searching, and exact editing help avoid messy shell output.
3. The same tool policy can hurt terminal-native tasks where direct bash
   iteration is the shortest path.
4. The next improvement should be adaptive tool policy:
   codebase-edit tasks should prefer structured tools, while terminal-build,
   data-processing, QEMU, package, and benchmark-specific tasks should allow
   faster bash-first behavior.
5. Evaluation discipline is now in place: the project has reproducible local
   A/B outputs for Terminal-Bench 2.1 and SWE-bench Pro.

## Recommended Next Steps

Priority 1: regression triage.

- Inspect the 10 Terminal-Bench regressions before changing core runtime code.
- Compare baseline and v2 trajectories for command/tool choices.
- Identify whether the failure came from prompt policy, tool overhead, missing
  context, edit friction, or verifier misunderstanding.

Priority 2: task-aware tool policy.

- Keep structured tools for SWE-bench-style codebase patch workflows.
- Use a lighter bash-first prompt for Terminal-Bench tasks.
- Consider a config-level policy switch instead of forcing one global behavior.

Priority 3: reporting and observability.

- Add trajectory-level telemetry for tool count, bash count, edit count,
  repeated reads, output truncation, and final verifier failure mode.
- Store lightweight comparison summaries under version control while keeping
  raw trajectories and logs out of Git.

Priority 4: rerun only changed policies.

- Re-test the 18 changed Terminal-Bench tasks first.
- Then run the full 89-task Terminal-Bench A/B again.
- For SWE-bench Pro, retest the 7 changed instances first before rerunning all
  30 tasks.

## Artifacts

Local artifacts from this run:

- `output/tbench21_89_baseline_deepseek_v4_pro_w6_step80/summary.json`
- `output/tbench21_89_v2_deepseek_v4_pro_w6_step80/summary.json`
- `output/tbench21_89_compare_deepseek_v4_pro_w6_step80.json`
- `logs/swebench_pro/deepseek_v4_pro_swebench_pro30_v2_structured_w10_step300_eval/summary.json`

The raw trajectory and verifier outputs are intentionally not committed because
they are large and environment-specific.

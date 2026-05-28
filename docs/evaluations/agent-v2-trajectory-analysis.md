# Agent V2 Trajectory Analysis

Date: 2026-05-28

This note analyzes the saved trajectories for the original baseline agent and
the current `agent-v2` runtime. It complements
`docs/evaluations/agent-v2-benchmark-report.md` by looking at how the agents
behaved, not only whether the final verifier passed.

## Inputs

Terminal-Bench 2.1:

- Baseline trajectories:
  `output/tbench21_89_baseline_deepseek_v4_pro_w6_step80`
- V2 trajectories:
  `output/tbench21_89_v2_deepseek_v4_pro_w6_step80`
- Total compared: 89 baseline trajectories and 89 v2 trajectories.

SWE-bench Pro:

- Baseline trajectories:
  `../mini-swe-agent/output/deepseek_v4_pro_swebench_pro10_appcwd_w10_step300`
  and
  `../mini-swe-agent/output/deepseek_v4_pro_swebench_pro10_30_appcwd_w10_step300`
- V2 trajectories:
  `output/deepseek_v4_pro_swebench_pro30_v2_structured_w10_step300`
- Total compared: 30 baseline trajectories and 30 v2 trajectories.
- Baseline rows 0-9 use the fixed eval summary:
  `../mini-swe-agent/logs/swebench_pro/deepseek_v4_pro_swebench_pro10_appcwd_w10_step300_eval_fixed/summary.json`.

## Executive Finding

By score, the baseline is still slightly better:

| Benchmark | Baseline | V2 | Delta |
| --- | ---: | ---: | ---: |
| Terminal-Bench 2.1 | 56/89 | 54/89 | -2 |
| SWE-bench Pro | 16/30 | 15/30 | -1 |

By trajectory quality, the picture is more mixed.

- Terminal-Bench v2 did not exercise the new structured file tools. It was
  effectively another bash-only run, so Terminal-Bench should not be used as
  evidence that structured tools help or hurt yet.
- SWE-bench Pro v2 did exercise structured tools heavily. It shows a real
  advantage on successful codebase-edit tasks: fewer model calls on passes,
  better working-directory discipline, and several baseline-only failures fixed.
- The main v2 weakness is failure-mode control. When v2 gets confused, it
  reads too much, retries edits too many times, and often produces broader or
  less disciplined patches than the baseline.

## Terminal-Bench 2.1 Trajectories

Terminal-Bench v2 used only `bash`; there were zero structured calls across all
89 tasks.

| Metric | Baseline All | V2 All | Baseline Pass | V2 Pass | Baseline Fail | V2 Fail |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Avg API calls | 35.75 | 35.40 | 28.30 | 29.00 | 48.39 | 45.29 |
| Avg bash calls | 40.63 | 40.18 | 32.71 | 33.02 | 54.06 | 51.23 |
| Avg structured calls | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Avg output chars | 504.7k | 293.5k | 69.4k | 48.2k | 1243.4k | 671.9k |
| Avg timeouts | 0.74 | 1.02 | 0.59 | 0.72 | 1.00 | 1.49 |
| Avg detected test commands | 0.44 | 0.43 | 0.36 | 0.67 | 0.58 | 0.06 |
| Avg detected edit commands | 3.36 | 2.69 | 3.29 | 2.19 | 3.48 | 3.46 |

Interpretation:

- Baseline wins Terminal-Bench by score.
- V2's Terminal-Bench run is not a structured-tool comparison. It mainly shows
  that the current v2 config can still run bash-style terminal tasks, but it is
  not better than the original agent there.
- V2 produced less total shell output, but had more timeout events and fewer
  test-like commands on failed tasks. That suggests failed v2 tasks often got
  stuck in construction or environment setup rather than reaching verifier-like
  feedback.

Changed Terminal-Bench tasks:

| Category | Tasks |
| --- | --- |
| V2-only pass | `adaptive-rejection-sampler`, `circuit-fibsqrt`, `filter-js-from-html`, `mteb-leaderboard`, `pytorch-model-cli`, `qemu-startup`, `regex-log`, `sqlite-with-gcov` |
| Baseline-only pass | `configure-git-webserver`, `mailman`, `merge-diff-arc-agi-task`, `qemu-alpine-ssh`, `reshard-c4-data`, `rstan-to-pystan`, `sam-cell-seg`, `sqlite-db-truncate`, `tune-mjcf`, `winning-avg-corewars` |

Notable Terminal-Bench observations:

- `configure-git-webserver`: baseline produced the expected content; v2
  submitted content with an extra suffix and failed exact-output verification.
- `qemu-startup`, `pytorch-model-cli`, and `regex-log`: v2 reached a working
  solution where baseline got stuck or missed environment dependencies.
- `sqlite-db-truncate` and `tune-mjcf`: v2 failures include external package
  fetch or `uvx` setup failures, so they should be treated as noisy regressions
  before drawing architectural conclusions.
- `winning-avg-corewars`: baseline reached a verifier-accepted warrior; v2 hit
  the step limit and never submitted.

## SWE-bench Pro Trajectories

SWE-bench Pro is the more important comparison for the v2 architecture because
v2 actually used structured tools.

| Metric | Baseline All | V2 All | Baseline Pass | V2 Pass | Baseline Fail | V2 Fail |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Avg API calls | 59.37 | 65.50 | 51.50 | 43.40 | 68.36 | 87.60 |
| Avg bash calls | 59.13 | 17.03 | 51.31 | 13.00 | 68.07 | 21.07 |
| Avg structured calls | 0.00 | 68.20 | 0.00 | 39.13 | 0.00 | 97.27 |
| Avg output chars | 121.6k | 1241.1k | 97.5k | 985.3k | 149.1k | 1497.0k |
| Avg timeouts | 0.17 | 1.80 | 0.19 | 1.67 | 0.14 | 1.93 |
| Avg `/testbed` path mistakes | 1.13 | 0.00 | 1.25 | 0.00 | 1.00 | 0.00 |
| Avg detected test commands | 2.80 | 2.23 | 2.81 | 2.07 | 2.79 | 2.40 |
| Avg detected shell edit commands | 2.57 | 0.63 | 2.06 | 0.60 | 3.14 | 0.67 |

V2 tool distribution across SWE-bench Pro:

| Tool | Calls |
| --- | ---: |
| `read_file` | 1316 |
| `grep` | 337 |
| `edit_file` | 333 |
| `bash` | 511 |
| `glob` | 60 |

Interpretation:

- V2 has a real workflow advantage on successful SWE-bench Pro tasks. It uses
  far fewer bash commands and fewer API calls than the baseline on passes.
- V2 completely eliminates the baseline's recurring `/testbed` path confusion
  on this Pro setup, because the v2 prompt/config consistently works in `/app`.
- V2 failures are expensive: failed v2 runs average 87.6 API calls and 97.3
  structured calls. The agent often keeps reading and editing instead of
  stopping to reassess.
- V2 is better at localizing source edits when it is already on the right path,
  but worse at patch hygiene when it chooses the wrong abstraction or broad
  migration.

## SWE-bench Pro Changed Instances

| Instance | Baseline | V2 | Trajectory diagnosis |
| --- | ---: | ---: | --- |
| `ansible-a26c...` | fail | pass | V2 used structured search/read/edit to thread `use_netrc` through the correct Ansible URL call sites. Baseline left a `NameError: use_netrc is not defined` and failed 2 tests. |
| `flipt-3b2c...` | fail | pass | Baseline hit a Go build failure. V2 made a more complete OFREP change and passed selected tests. |
| `flipt-e42d...` | fail | pass | V2 passed where baseline had setup/build failures, but the patch was broad and included generated or dependency files. This is a score win, but not ideal patch hygiene. |
| `NodeBB-a5af...` | pass | fail | Baseline made a focused 4-file patch. V2 changed 104 files, including 99 localization files, and failed. This is the clearest over-editing regression. |
| `element-web-33e...` | pass | fail | Both created `KeyBindingsManager.ts`, but baseline's 112-line file passed; v2's 131-line implementation failed 4 of 5 tests. |
| `element-web-5df...` | pass | fail | Baseline touched 4 relevant files and passed. V2 touched 3 files, missed one behavior area, and failed 7 tests. |
| `vuls-4074...` | pass | fail | Baseline changed only source. V2 also modified `parser_test.go`, violated the intended boundary, and failed `TestParse`. |

Patch-shape comparison:

| Metric | Baseline Passes | V2 Passes | Baseline Failures | V2 Failures |
| --- | ---: | ---: | ---: | ---: |
| Avg files changed | 2.75 | 3.53 | 4.57 | 10.40 |
| Median files changed | 3 | 3 | 4 | 3 |
| Avg patch bytes | 7.1k | 11.9k | 10.1k | 14.8k |
| Patches touching tests | 0 | 0 | 1 | 3 |
| Patches touching generated/dependency files | 0 | 1 | 0 | 0 |
| Patches touching locale/i18n files | 0 | 0 | 0 | 1 |

The patch-shape data explains much of the v2 regression: v2 failures are not
just wrong; they are often larger and more invasive.

## Which Agent Is Better?

Current overall answer: the baseline is still better as a benchmark competitor,
because it passes more tasks on both evaluated sets.

Engineering answer: v2 is the better foundation for SWE-bench-style work, but
only after failure-mode controls are added.

Baseline strengths:

- Direct and efficient for terminal-native work.
- Smaller patches on successful SWE-bench Pro tasks.
- Less prone to long structured-tool loops.
- Better current aggregate score.

V2 strengths:

- Better workspace discipline on SWE-bench Pro.
- Stronger source-code navigation model when the issue maps cleanly to search,
  bounded reads, and exact edits.
- Fewer model calls on successful SWE-bench Pro tasks.
- Solves several baseline misses that required coordinated edits across call
  sites.

V2 weaknesses to fix next:

- Add patch hygiene guardrails: warn or block when patches touch too many files,
  tests, locale files, generated files, or dependency lockfiles unless explicitly
  justified.
- Add a failure-loop breaker: if structured reads/edits exceed a threshold
  without new verifier signal, force a summary and a narrower plan.
- Improve edit policy: prefer source-only minimal patches, and run `git diff`
  earlier so the model sees patch blast radius before final submission.
- Add benchmark-specific policy: Terminal-Bench should stay bash-first, while
  SWE-bench should use structured tools.
- Add trajectory telemetry to the runner so future A/B reports include tool
  counts, patch stats, path mistakes, and verifier failure categories by default.

## Optimization Priority

The best next optimization is not another broad architecture rewrite. It is a
targeted v2 policy pass:

1. Enforce patch hygiene in prompt and runtime.
2. Add source/test/generated/locale path risk detection around `edit_file` and
   final patch submission.
3. Add loop limits for repeated `read_file`, `grep`, and failed `edit_file`
   calls.
4. Re-run only the 7 changed SWE-bench Pro instances first.
5. Then re-run the full 30-task Pro set and the Terminal-Bench changed subset.

This keeps the project resume-credible: the narrative is not "v2 is already
better", but "v2 exposes a stronger architecture, measured with A/B, and the
next work is driven by trajectory evidence."

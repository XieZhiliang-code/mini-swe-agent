#!/usr/bin/env python3
"""Run mini-swe-agent configs on a local Terminal-Bench task directory."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import json
import random
import re
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    import tomli as tomllib

from minisweagent.agents import get_agent
from minisweagent.config import get_config_from_spec
from minisweagent.environments import get_environment
from minisweagent.models import get_model
from minisweagent.utils.serialize import UNSET, recursive_merge

_PRINT_LOCK = threading.Lock()


def log(message: str) -> None:
    with _PRINT_LOCK:
        print(message, flush=True)


def load_task(task_dir: Path) -> dict[str, Any]:
    data = tomllib.loads((task_dir / "task.toml").read_text(encoding="utf-8"))
    env = data.get("environment", {})
    task = data.get("task", {})
    verifier = data.get("verifier", {})
    agent = data.get("agent", {})
    return {
        "task_name": task_dir.name,
        "task_dir": task_dir,
        "instruction": (task_dir / "instruction.md").read_text(encoding="utf-8"),
        "docker_image": env["docker_image"],
        "cpus": env.get("cpus"),
        "memory_mb": env.get("memory_mb"),
        "allow_internet": env.get("allow_internet", True),
        "agent_timeout_sec": int(agent.get("timeout_sec") or 900),
        "verifier_timeout_sec": int(verifier.get("timeout_sec") or 900),
        "metadata": {
            "schema_version": data.get("schema_version"),
            "task": task,
            "environment": env,
            "verifier": verifier,
            "agent": agent,
        },
    }


def list_tasks(tasks_dir: Path, *, limit: int = 0, slice_spec: str = "", filter_spec: str = "", shuffle: bool = False):
    task_dirs = sorted(path.parent for path in tasks_dir.glob("*/task.toml"))
    if filter_spec:
        task_dirs = [path for path in task_dirs if re.search(filter_spec, path.name)]
    if shuffle:
        random.seed(42)
        random.shuffle(task_dirs)
    if slice_spec:
        values = [int(value) if value else None for value in slice_spec.split(":")]
        task_dirs = task_dirs[slice(*values)]
    if limit:
        task_dirs = task_dirs[:limit]
    return [load_task(path) for path in task_dirs]


def build_run_args(task: dict[str, Any], extra_run_args: list[str]) -> list[str]:
    run_args = ["--rm"]
    if task.get("cpus"):
        run_args.extend(["--cpus", str(task["cpus"])])
    if task.get("memory_mb"):
        run_args.extend(["--memory", f"{task['memory_mb']}m"])
    if not task.get("allow_internet", True):
        run_args.extend(["--network", "none"])
    run_args.extend(extra_run_args)
    return run_args


def build_config(args: argparse.Namespace, task: dict[str, Any], task_output_dir: Path) -> dict[str, Any]:
    configs = [get_config_from_spec(spec) for spec in args.config]
    overrides: dict[str, Any] = {
        "environment": {
            "environment_class": "docker",
            "image": task["docker_image"],
            "cwd": "/app",
            "timeout": args.command_timeout,
            "container_timeout": args.container_timeout,
            "interpreter": ["bash", "-lc"],
            "run_args": build_run_args(task, args.docker_run_arg),
        },
        "agent": {
            "output_path": task_output_dir / f"{task['task_name']}.traj.json",
            "cost_limit": args.cost_limit if args.cost_limit is not None else UNSET,
            "step_limit": args.step_limit if args.step_limit is not None else UNSET,
        },
        "model": {
            "model_name": args.model or UNSET,
            "model_class": args.model_class or UNSET,
        },
    }
    if args.api_base:
        overrides["model"]["model_kwargs"] = {"api_base": args.api_base}
    return recursive_merge(*configs, overrides)


def run_command(cmd: list[str], *, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def docker_cp(src: str, dest: str, *, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return run_command(["docker", "cp", src, dest], timeout=timeout)


def run_verifier(env, task: dict[str, Any], task_output_dir: Path) -> dict[str, Any]:
    assert env.container_id, "container not started"
    setup = env.execute({"command": "rm -rf /tests /logs/verifier && mkdir -p /logs/verifier"}, timeout=30)
    tests_src = str(task["task_dir"] / "tests")
    copy_result = docker_cp(tests_src, f"{env.container_id}:/tests", timeout=300)
    if setup["returncode"] != 0 or copy_result.returncode != 0:
        return {
            "reward": 0,
            "verifier_returncode": -1,
            "verifier_output": setup.get("output", "") + copy_result.stdout,
            "verifier_exception": setup.get("exception_info", ""),
        }

    verifier_result = env.execute({"command": "bash /tests/test.sh"}, timeout=task["verifier_timeout_sec"])
    reward_result = env.execute({"command": "cat /logs/verifier/reward.txt 2>/dev/null || true"}, timeout=10)
    reward_text = reward_result.get("output", "").strip()
    reward = 1 if reward_text == "1" else 0

    verifier_dir = task_output_dir / "verifier"
    verifier_dir.mkdir(parents=True, exist_ok=True)
    (task_output_dir / "verifier_output.txt").write_text(verifier_result.get("output", ""), encoding="utf-8")
    docker_cp(f"{env.container_id}:/logs/verifier", str(verifier_dir), timeout=300)
    return {
        "reward": reward,
        "reward_text": reward_text,
        "verifier_returncode": verifier_result.get("returncode"),
        "verifier_output": verifier_result.get("output", ""),
        "verifier_exception": verifier_result.get("exception_info", ""),
    }


def process_task(task: dict[str, Any], output_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    task_name = task["task_name"]
    task_output_dir = output_dir / task_name
    result_path = task_output_dir / "result.json"
    if result_path.exists() and not args.redo_existing:
        return json.loads(result_path.read_text(encoding="utf-8"))

    task_output_dir.mkdir(parents=True, exist_ok=True)
    start_time = time.time()
    env = None
    agent = None
    result: dict[str, Any] = {
        "task_name": task_name,
        "docker_image": task["docker_image"],
        "started_at": start_time,
        "reward": 0,
        "exit_status": "",
        "error": "",
    }
    try:
        config = build_config(args, task, task_output_dir)
        result["config"] = {
            "config_specs": args.config,
            "agent_class": config.get("agent", {}).get("agent_class", "default"),
            "model_name": config.get("model", {}).get("model_name", ""),
        }
        model = get_model(config=config.get("model", {}))
        env = get_environment(config.get("environment", {}), default_type="docker")
        agent = get_agent(model, env, config.get("agent", {}), default_type="default")
        agent_info = agent.run(task["instruction"])
        result.update(
            {
                "exit_status": agent_info.get("exit_status", ""),
                "submission": agent_info.get("submission", ""),
                "agent_cost": getattr(agent, "cost", 0.0),
                "agent_calls": getattr(agent, "n_calls", 0),
            }
        )
        verifier_info = run_verifier(env, task, task_output_dir)
        result.update(verifier_info)
    except Exception as exc:
        result.update(
            {
                "exit_status": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        )
        if agent is not None:
            result["agent_cost"] = getattr(agent, "cost", 0.0)
            result["agent_calls"] = getattr(agent, "n_calls", 0)
    finally:
        if env is not None:
            try:
                env.cleanup()
            except Exception:
                pass
        result["duration_sec"] = time.time() - start_time
        result["finished_at"] = time.time()
        result_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return result


def summarize(results: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for result in results if result.get("reward") == 1)
    errored = sum(1 for result in results if result.get("error"))
    summary = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "errored": errored,
        "pass_rate": passed / total if total else 0.0,
        "tasks": [
            {
                "task_name": result.get("task_name"),
                "reward": result.get("reward", 0),
                "exit_status": result.get("exit_status", ""),
                "agent_calls": result.get("agent_calls", 0),
                "agent_cost": result.get("agent_cost", 0.0),
                "duration_sec": result.get("duration_sec", 0.0),
                "error": result.get("error", ""),
            }
            for result in sorted(results, key=lambda item: item.get("task_name", ""))
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks-dir", required=True, type=Path)
    parser.add_argument("-c", "--config", action="append", required=True)
    parser.add_argument("-o", "--output", required=True, type=Path)
    parser.add_argument("-w", "--workers", type=int, default=1)
    parser.add_argument("--model", default="")
    parser.add_argument("--model-class", default="")
    parser.add_argument("--api-base", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--slice", dest="slice_spec", default="")
    parser.add_argument("--filter", dest="filter_spec", default="")
    parser.add_argument("--shuffle", action="store_true")
    parser.add_argument("--redo-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--command-timeout", type=int, default=120)
    parser.add_argument("--container-timeout", default="2h")
    parser.add_argument("--cost-limit", type=float, default=None)
    parser.add_argument("--step-limit", type=int, default=None)
    parser.add_argument("--docker-run-arg", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    tasks = list_tasks(
        args.tasks_dir,
        limit=args.limit,
        slice_spec=args.slice_spec,
        filter_spec=args.filter_spec,
        shuffle=args.shuffle,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        for task in tasks:
            print(f"{task['task_name']}\t{task['docker_image']}")
        print(f"tasks={len(tasks)} output={args.output}")
        return 0

    log(f"Running {len(tasks)} Terminal-Bench task(s) with workers={args.workers}. Output: {args.output}")
    results: list[dict[str, Any]] = []
    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_task, copy.deepcopy(task), args.output, args): task for task in tasks}
        for future in concurrent.futures.as_completed(futures):
            task = futures[future]
            completed += 1
            try:
                result = future.result()
            except Exception as exc:
                result = {
                    "task_name": task["task_name"],
                    "reward": 0,
                    "exit_status": type(exc).__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            results.append(result)
            log(
                f"[{completed:03d}/{len(tasks):03d}] {result.get('task_name')} "
                f"reward={result.get('reward', 0)} status={result.get('exit_status', '')} "
                f"calls={result.get('agent_calls', 0)}"
            )
            summarize(results, args.output)

    summary = summarize(results, args.output)
    log(f"Done: {summary['passed']}/{summary['total']} passed ({summary['pass_rate']:.1%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

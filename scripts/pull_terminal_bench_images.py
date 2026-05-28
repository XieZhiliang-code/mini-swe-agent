#!/usr/bin/env python3
"""Pull Terminal-Bench task Docker images from a mirror and tag originals."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path


def run(cmd: list[str], *, log) -> int:
    log.write("$ " + " ".join(cmd) + "\n")
    log.flush()
    proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    log.flush()
    return proc.returncode


def image_exists(image: str) -> bool:
    return subprocess.run(
        ["docker", "image", "inspect", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def image_size(image: str) -> int:
    output = subprocess.check_output(["docker", "image", "inspect", image, "--format", "{{.Size}}"], text=True)
    return int(output.strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks-dir", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=44)
    parser.add_argument("--mirror", default="docker.1ms.run")
    parser.add_argument("--log", required=True, type=Path)
    args = parser.parse_args()

    items: list[tuple[str, str]] = []
    for task_file in sorted(args.tasks_dir.glob("*/task.toml"))[: args.limit]:
        text = task_file.read_text()
        match = re.search(r'docker_image = "([^"]+)"', text)
        if not match:
            continue
        items.append((task_file.parent.name, match.group(1)))

    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open("a", buffering=1) as log:
        log.write(f"\n=== pull start {time.strftime('%Y-%m-%d %H:%M:%S')} images={len(items)} ===\n")
        ok = 0
        failures: list[tuple[str, str, str]] = []
        for index, (task_name, image) in enumerate(items, 1):
            mirror_image = f"{args.mirror}/{image}"
            print(f"[{index:02d}/{len(items)}] {task_name} {image}", flush=True)
            log.write(f"\n[{index:02d}/{len(items)}] {task_name} {image}\n")

            if not image_exists(image):
                rc = run(["docker", "pull", mirror_image], log=log)
                if rc != 0:
                    failures.append((task_name, image, f"pull rc={rc}"))
                    print(f"FAILED pull {image}", flush=True)
                    continue
                rc = run(["docker", "tag", mirror_image, image], log=log)
                if rc != 0:
                    failures.append((task_name, image, f"tag rc={rc}"))
                    print(f"FAILED tag {image}", flush=True)
                    continue

            size = image_size(image)
            ok += 1
            log.write(f"OK {image} size_bytes={size}\n")
            print(f"OK {image} size={size / 1024 / 1024:.1f} MiB", flush=True)

        log.write(f"=== done ok={ok} fail={len(failures)} ===\n")
        for failure in failures:
            log.write(f"FAIL {failure}\n")
        if failures:
            print(f"Failed {len(failures)} image(s); see {args.log}", flush=True)
            return 1
        print(f"Pulled/tagged {ok} image(s). Log: {args.log}", flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

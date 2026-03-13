#!/usr/bin/env python3
"""Run the generated Amazon Connect regression suite.

What it does:
- (Optional) regenerates the Connect regression manifest + generated scenarios
- validates all discovered scenarios
- optionally executes the scenarios in batch via voice_tester CLI

This is designed for unattended runs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Set


def find_latest_manifest(repo_root: Path) -> Path:
    gen_root = repo_root / "voice_tester" / "scenarios" / "instance_tests" / "generated"
    dirs = sorted([p for p in gen_root.iterdir() if p.is_dir() and p.name.startswith("connect_regression_")])
    if not dirs:
        raise FileNotFoundError(f"No connect_regression_* directories found under: {gen_root}")
    manifest = dirs[-1] / "manifest.json"
    if not manifest.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest}")
    return manifest


def collect_scenarios(manifest: Dict[str, Any], *, include_existing: bool, include_generated: bool) -> List[str]:
    paths: List[str] = []
    for entry in manifest.get("scenarios", []) or []:
        if include_existing:
            paths.extend(entry.get("existing_scenarios", []) or [])
        if include_generated:
            paths.extend(entry.get("generated_scenarios", []) or [])

    # De-dupe while preserving order
    seen: Set[str] = set()
    out: List[str] = []
    for p in paths:
        if p and p not in seen:
            out.append(p)
            seen.add(p)
    return out


def run_cmd(cmd: List[str]) -> int:
    return subprocess.run(cmd, check=False).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Connect regression suite (validate + optional execution)")
    ap.add_argument("--regions", nargs="+", default=["us-east-1", "us-west-2"], help="Regions to scan")
    ap.add_argument("--out-dir", default=None, help="Optional output dir to pass to the generator")
    ap.add_argument("--skip-generate", action="store_true", help="Skip regeneration; use latest manifest")
    ap.add_argument("--manifest", default=None, help="Path to manifest.json (overrides latest)")

    ap.add_argument("--execute", action="store_true", help="Execute tests after validation")
    ap.add_argument("--mode", choices=["pstn", "webrtc"], default="pstn", help="Execution mode")
    ap.add_argument("--include-existing", action="store_true", help="Include existing (non-generated) scenarios")
    ap.add_argument("--wait", action="store_true", help="Wait for each test to complete")
    ap.add_argument("--timeout", type=int, default=300, help="Wait timeout (seconds)")
    ap.add_argument("--include-recording", action="store_true", help="Print recording URLs (requires --wait)")

    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]

    if not args.skip_generate:
        gen_cmd = [sys.executable, "scripts/generate_connect_regression_tests.py", "--regions", *args.regions]
        if args.out_dir:
            gen_cmd += ["--out-dir", args.out_dir]
        rc = run_cmd(gen_cmd)
        if rc != 0:
            return rc

    manifest_path = Path(args.manifest).expanduser() if args.manifest else find_latest_manifest(repo_root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # By default, execute the generated regression scenarios only.
    # Legacy scenarios may be authored for other runners/modes.
    scenarios = collect_scenarios(
        manifest,
        include_existing=args.include_existing,
        include_generated=True,
    )
    if not scenarios:
        print(f"No scenarios found in manifest: {manifest_path}")
        return 1

    # Validate selected scenarios
    validate_failures = 0
    for scen in scenarios:
        rc = run_cmd([sys.executable, "-W", "ignore::RuntimeWarning", "-m", "voice_tester.cli", "validate", scen])
        if rc != 0:
            validate_failures += 1

    if validate_failures:
        print(f"Validation failures: {validate_failures}/{len(scenarios)}")
        return 1

    if not args.execute:
        print(f"Validated {len(scenarios)} scenarios OK (no execution; use --execute to run)")
        return 0

    # Execute
    exec_failures = 0
    for scen in scenarios:
        cmd = [
            sys.executable,
            "-W",
            "ignore::RuntimeWarning",
            "-m",
            "voice_tester.cli",
            "test",
            scen,
            "--mode",
            args.mode,
        ]
        if args.wait:
            cmd.append("--wait")
            cmd += ["--timeout", str(args.timeout)]

        if args.include_recording:
            cmd.append("--include-recording")

        rc = run_cmd(cmd)
        if rc != 0:
            exec_failures += 1

    print(f"Executed {len(scenarios)} scenarios; failures={exec_failures}")
    return 0 if exec_failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

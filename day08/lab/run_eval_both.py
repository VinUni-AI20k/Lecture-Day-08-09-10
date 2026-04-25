"""
run_eval_both.py
================
Runner nho de chay eval.py voi ca 2 mode:
  1. rule-based
  2. llm-as-judge
"""

import subprocess
import sys
from pathlib import Path


def run_mode(mode: str) -> int:
    eval_path = Path(__file__).parent / "eval.py"
    cmd = [sys.executable, str(eval_path), "--scoring-mode", mode]

    print("\n" + "=" * 70)
    print(f"Running eval.py with scoring mode: {mode}")
    print("=" * 70)

    result = subprocess.run(cmd, check=False)
    return result.returncode


if __name__ == "__main__":
    exit_codes = {
        "rule": run_mode("rule"),
        "llm": run_mode("llm"),
    }

    print("\nSummary:")
    for mode, code in exit_codes.items():
        status = "OK" if code == 0 else f"FAILED ({code})"
        print(f"  {mode}: {status}")

    if any(code != 0 for code in exit_codes.values()):
        sys.exit(1)

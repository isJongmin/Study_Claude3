"""전체 검사: ruff -> pytest -> vue-tsc -> vite build -> (--e2e) playwright. 단계별 PASS/FAIL, 실패는 꼬리 40줄만.
사용: python scripts/verify.py [--e2e] [--only ruff|pytest|tsc|build|e2e]"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = str(ROOT / "backend" / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
FE = ROOT / "frontend"
STEPS = {
    "ruff": ([PY, "-m", "ruff", "check", "backend", "scripts"], ROOT),
    "pytest": ([PY, "-m", "pytest", "-q", "backend/tests"], ROOT),
    "tsc": ("npx vue-tsc --noEmit", FE),
    "build": ("npx vite build", FE),
    "e2e": ("npx playwright test --reporter=line", FE),
}


sys.stdout.reconfigure(errors="replace")  # cp949 콘솔에서도 죽지 않게


def run(name):
    cmd, cwd = STEPS[name]
    p = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok = p.returncode == 0
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        print("\n".join((p.stdout + p.stderr).strip().splitlines()[-40:]))
    return ok


def main():
    a = sys.argv[1:]
    if "--only" in a:
        names = [a[a.index("--only") + 1]]
    else:
        names = ["ruff", "pytest"] + (["tsc", "build"] if (FE / "package.json").exists() else []) + (["e2e"] if "--e2e" in a else [])
    res = {}
    for n in names:
        res[n] = run(n)
        if not res[n] and n in ("build",):
            break
    print("결과:", " ".join(f"{k}={'PASS' if v else 'FAIL'}" for k, v in res.items()))
    return 0 if all(res.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

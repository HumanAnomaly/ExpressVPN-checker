"""Terminal UI built on Rich: banner, config table, progress, summary."""
import sys

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

console = Console(legacy_windows=sys.platform == "win32" and
                  (sys.stdout.encoding or "").lower() not in ("utf-8", "utf8"))


def print_banner() -> None:
    console.print(Panel(
        "[bold]CHECKER[/bold] [dim]- python cli[/dim]",
        title="[bold white on red] EXPRESS VPN [/]",
        width=48,
        style="red",
    ))
    console.print("[dim]        created by HumanAnomaly[/dim]")
    console.print("[dim]        github.com/HumanAnomaly/ExpressVPN-checker[/dim]\n")


def print_config(n_combos: int, threads: int, timeout: int, proxies: list[str]) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("key", style="dim")
    table.add_column("value", style="bold")
    table.add_row("combos", str(n_combos))
    table.add_row("threads", str(threads))
    table.add_row("timeout", f"{timeout}s")
    table.add_row("mode", f"proxies ({len(proxies)})" if proxies else "direct")
    console.print(Panel(table, width=48, border_style="dim"))


def make_progress(total: int) -> tuple[Progress, int]:
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=24),
        TaskProgressColumn(),
        TextColumn("HIT:{task.fields[hit]} FAIL:{task.fields[fail]}"),
        console=console,
        transient=True,
    )
    task = progress.add_task("checking", total=total, hit=0, fail=0)
    return progress, task


def print_hit(email: str, plan: str, expire: str, days: str) -> None:
    console.print(f"[green][+] HIT {email}[/green]  plan=[bold]{plan}[/bold] exp={expire} ({days}d)")


def print_fail(email: str, reason: str) -> None:
    console.print(f"[dim][-] FAIL {email} :: {reason[:80]}[/dim]")


def print_summary(done: int, hits: int, fails: int, elapsed: float, hit_path: str) -> None:
    rate = done / max(elapsed, 0.1)
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("key", style="dim")
    table.add_column("value")
    table.add_row("DONE", "")
    table.add_row("time", f"{elapsed:.1f}s ({rate:.2f}/s)")
    table.add_row("total", f"{done}   [green]hit: {hits}[/green]   [red]fail: {fails}[/red]")
    table.add_row("hits", hit_path)
    console.print(Panel(table, width=48, border_style="dim"))
    console.print("[dim]  Stashed. created by HumanAnomaly.[/dim]")

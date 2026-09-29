"""Argument parsing and top-level orchestration."""
import argparse
import os
import shutil
import subprocess
import sys

from .runner import load_combos, load_proxies, run
from .ui import console, print_banner, print_config


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="ExpressVPN checker - created by HumanAnomaly")
    ap.add_argument("input", help="combos.txt file OR single 'email:pass' combo")
    ap.add_argument("-t", "--threads", type=int, default=10)
    ap.add_argument("-o", "--output", default="output")
    ap.add_argument("--proxy", default=None, help="single proxy url (http://user:pass@host:port)")
    ap.add_argument("--proxies", default=None, help="proxy list file (round-robin)")
    ap.add_argument("--timeout", type=int, default=20)
    return ap


def ensure_deps() -> None:
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher  # noqa: F401
    except ImportError:
        console.print("[yellow][*] installing cryptography (for AES decrypt)...[/yellow]")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "cryptography", "requests"])


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    print_banner()
    if shutil.which("openssl") is None:
        console.print("[red][!] openssl not found in PATH — envelope encrypt will fail.[/red]")
        console.print("[dim]    install: https://openssl.org / `choco install openssl` / `apt install openssl`[/dim]\n")

    if os.path.isfile(args.input):
        combos = load_combos(args.input)
    elif ":" in args.input and "@" in args.input:
        email, password = args.input.strip().split(":", 1)
        combos = [(email.strip(), password.strip())]
        console.print(f"[blue]>>[/blue] single combo mode: [bold]{email.strip()}[/bold]")
    else:
        console.print(f"[red][!] input not found: {args.input}[/red]")
        sys.exit(1)
    if not combos:
        console.print("[red][!] no valid combos (need email:pass lines).[/red]")
        sys.exit(1)

    proxies = load_proxies(args.proxies, args.proxy)
    if args.proxies and proxies:
        console.print(f"[blue]>>[/blue] {len(proxies)} proxies loaded (round-robin)")
    elif args.proxy:
        console.print("[blue]>>[/blue] single proxy mode")

    ensure_deps()
    print_config(len(combos), args.threads, args.timeout, proxies)
    run(combos, proxies, args.threads, args.timeout, args.output)

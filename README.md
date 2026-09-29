<p align="center">
  <img src="assets/expressvpn-icon.jpeg" width="120" alt="ExpressVPN Checker">
</p>

<h1 align="center">ExpressVPN Checker</h1>

<p align="center">
  Automated tool for checking ExpressVPN account credentials and status.
</p>

<p align="center">
  <a href="https://github.com/HumanAnomaly/ExpressVPN-checker"><img src="https://img.shields.io/github/stars/HumanAnomaly/ExpressVPN-checker?style=flat-square&logo=github" alt="stars"></a>
  <a href="https://github.com/HumanAnomaly/ExpressVPN-checker/blob/main/LICENSE"><img src="https://img.shields.io/github/license/HumanAnomaly/ExpressVPN-checker?style=flat-square" alt="license"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python" alt="python">
</p>

> **Education only.** Only test accounts you own or have permission to check.

## Install

```bash
pip install -r requirements.txt
```

Needs the `openssl` binary in PATH. Windows: `choco install openssl`.

## Usage

```bash
python checker.py "user@example.com:ExamplePass123!"
python checker.py combos.txt -t 20
python checker.py combos.txt --proxies proxies.txt -t 20
```

| Flag | Default | Description |
|---|---|---|
| `-t, --threads` | `10` | Concurrent checks |
| `-o, --output` | `output` | Result folder |
| `--proxy` / `--proxies` | — | Single proxy URL or list file (round-robin) |
| `--timeout` | `20` | Seconds per request |

Results: `output/hits_<timestamp>.txt` for valid accounts, `output/all.txt` for the full log.

## How it works

```mermaid
flowchart LR
    A[combo] --> B[gzip + RSA encrypt]
    B --> C[POST /credentials]
    C --> D[AES decrypt]
    D --> E[POST /batch]
    E --> F{HIT / FAIL}
```

Each combo is gzipped, RSA-encrypted with the ExpressVPN public cert, and POSTed with HMAC-SHA1 signatures. The encrypted reply is AES-decrypted into an access token, which is then used for a subscription lookup (plan, expiry, payment). Expired accounts count as FAIL.

## Structure

```
checker.py            entry point
src/                  config · crypto · api · runner · ui · cli
```

## License

MIT — see [LICENSE](LICENSE).

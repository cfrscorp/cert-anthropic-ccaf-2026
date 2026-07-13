# Claude Certified Architect – Foundations (CCAF) Exam Prep

Study materials and a hands-on lab program for the **Claude Certified Architect –
Foundations (CCAF)** certification. The exam validates practical judgment about
building production applications with **Claude Code, the Claude Agent SDK, the
Claude API, and the Model Context Protocol (MCP)**.

This repo pairs the official exam guide with a buildable, testable lab curriculum
so you can gain hands-on experience with *every* feature, property, concept, and
topic the exam covers — not just read about them.

## What's here

| Path | What it is |
|------|------------|
| [`anthropic-ccaf-exam-guide-2026.md`](anthropic-ccaf-exam-guide-2026.md) | The exam guide: 5 domains, 30 task statements, 6 scenarios, sample questions, prep exercises. |
| [`labs/`](labs/) | 25 hands-on labs + a shared test harness. Start at [`labs/README.md`](labs/README.md). |
| [`labs/README.md`](labs/README.md) | Master matrix: labs by dependency tier & difficulty, with effort estimates and a full task-statement → lab / scenario → capstone traceability map. |
| [`labs/_shared/`](labs/_shared/) | Reusable test harness (deterministic mock Claude client, `starter`/`solution` switching, opt-in LLM grading). See [`labs/_shared/README.md`](labs/_shared/README.md). |
| [`study/`](study/) | A local, offline study app — practice quiz, flashcards, concept explainers (with code samples), browsable labs, and a readiness dashboard. Run: `uv run study/serve.py`. See [`study/README.md`](study/README.md). |
| `.claude/` | Project Claude Code config (enables the `pyright-lsp` and `agent-sdk-dev` plugins). |

## The lab program at a glance

- **25 labs** across 5 dependency tiers (Foundations → Capstones), ordered so
  prerequisites come first, then by difficulty (1–10). ~48 hours of hands-on effort.
- **Full coverage:** every task statement (1.1–5.6) and every exam scenario (S1–S6)
  maps to at least one lab — see the traceability tables in [`labs/README.md`](labs/README.md).
- **Each lab folder** contains: `README.md` (instructions), `SOLUTION.md` (reference
  key + why-the-distractors-are-wrong), `starter/` (scaffold you fill in), `solution/`
  (reference implementation), `tests/` (automated checks), and any config artifacts
  (`.claude/rules`, `.mcp.json`, `SKILL.md`, CI YAML, sample docs).
- **Tests are deterministic and offline by default:** labs mock the Claude API via
  `labs/_shared/mock_anthropic.py`, so a plain test run needs no API key and costs
  nothing. A handful of inherently semantic checks are marked `llm` and run only when
  you opt in with an API key.

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/) — drives all Python scripts and tests (no manual venv needed)
- [Claude Code](https://docs.claude.com/claude-code) — for the configuration-oriented labs
- Optional: an `ANTHROPIC_API_KEY` to exercise the live end-to-end and `-m llm` paths

## Quick start

```bash
git clone https://github.com/craigforr/cert-anthropic-ccaf-2026
cd cert-anthropic-ccaf-2026/labs

uv run pytest lab-03-agentic-loop        # test YOUR work on one lab (its starter/)
uv run pytest                            # test your work across all labs
LAB_TARGET=solution uv run pytest        # run the reference solutions (all green)
ANTHROPIC_API_KEY=sk-... uv run pytest -m llm   # add the optional semantic checks
```

Suggested workflow per lab: read its `README.md` (note prerequisites) → fill in
`starter/` until `uv run pytest lab-NN-...` passes → compare against `SOLUTION.md`
and `solution/` for the *why*, not just the *what*.

## Study path

Work the labs in the order given in [`labs/README.md`](labs/README.md) (dependency
tier, then difficulty). Tier 0–1 build the core primitives (agentic loop, tool use,
structured output, Claude Code config); Tier 2–3 layer on error handling,
orchestration, and context management; the Tier 4 capstones integrate everything
into the six exam scenarios.

## Share the study app on your LAN (LAN-only)

By default `uv run study/serve.py` binds to `127.0.0.1` — reachable only from the
machine running it. You can share it with other devices **on your local network**
(a study group, a second laptop, a tablet) while keeping it **off the public
internet**.

**Why this stays LAN-only:** home/office routers do not forward inbound connections
from the internet by default, so binding the server to all local interfaces exposes
it only to devices on the same network. Keep it that way by following two rules:
**(1)** never add a port-forwarding / NAT rule on your router (and don't use a tunnel
like ngrok/Cloudflare Tunnel), and **(2)** scope your OS firewall to your *private*
network, as below. Only use this on a trusted network (home/office) — never on public
Wi‑Fi (cafés, airports, hotels, conferences).

**Start the server bound to all local interfaces**, on a fixed port, from the repo root:

```bash
uv run study/serve.py --host 0.0.0.0 --port 8000
```

On the host machine itself, use `http://localhost:8000/web/`. Other devices use
`http://<your-LAN-IP>:8000/web/` (find `<your-LAN-IP>` below — it looks like
`192.168.x.x` or `10.x.x.x`). There is **no authentication** — anyone on the LAN who
opens the URL can view the app (it serves read-only content; each person's progress
stays in their own browser).

### Windows 11

1. **Set the network to Private.** Settings → Network & internet → Wi‑Fi (or Ethernet)
   → click your connected network → set **Network profile type = Private**. (Windows
   only shares on Private networks; Public blocks inbound.)
2. **Find your LAN IP.** Open **Command Prompt** and run `ipconfig`; note the **IPv4
   Address** for your active adapter (e.g. `192.168.1.42`).
3. **Allow the port on the Private profile only.** Open **PowerShell as Administrator**
   and run:
   ```powershell
   New-NetFirewallRule -DisplayName "CCAF Study (LAN only)" -Direction Inbound `
     -Action Allow -Protocol TCP -LocalPort 8000 -Profile Private
   ```
   This permits inbound TCP 8000 on Private networks only — never on Public.
4. **Start the server:** `uv run study/serve.py --host 0.0.0.0 --port 8000`.
5. From another device on the same network, open `http://<IPv4-from-step-2>:8000/web/`.
6. **When done**, stop the server (Ctrl+C) and remove the rule:
   ```powershell
   Remove-NetFirewallRule -DisplayName "CCAF Study (LAN only)"
   ```

### macOS 26+

1. **Confirm you're on a trusted private network** (home/office Wi‑Fi or Ethernet), not
   a public hotspot.
2. **Find your LAN IP.** System Settings → Network → select your active Wi‑Fi/Ethernet
   → **Details… → TCP/IP** → note the **IP Address** (e.g. `192.168.1.23`). Or in
   Terminal: `ipconfig getifaddr en0` (Wi‑Fi) — try `en1` if that's blank (Ethernet).
3. **Firewall (application-based on macOS).** If the firewall is on
   (System Settings → Network → Firewall), the first time you start the server macOS
   prompts *"Do you want to allow incoming network connections?"* for the Python/`uv`
   binary — choose **Allow**. (You can leave the firewall enabled; under **Firewall
   Options…** the interpreter should be set to *Allow incoming connections*.) macOS's
   firewall has no per-port rules — LAN-only is guaranteed by rules (1) and (2) above,
   not by the firewall.
4. **Start the server:** `uv run study/serve.py --host 0.0.0.0 --port 8000`.
5. From another device on the same network, open `http://<IP-from-step-2>:8000/web/`.
6. **When done**, stop the server (Ctrl+C). Do **not** enable System Settings → General
   → Sharing → *Internet Sharing* (that changes your network exposure).

### Sanity check & teardown

- Verify from the host that it's listening on the LAN: another device on the same
  network should load the URL; a device on a *different* network (e.g. cellular, not the
  Wi‑Fi) should **not**.
- Stop sharing at any time with Ctrl+C. The app is fully static/offline — no data leaves
  your network.

## Notes

- Derived from the publicly distributed CCAF exam guide.
- Test suite status: `LAB_TARGET=solution uv run pytest` → 376 passed, 3 `llm`-marked
  tests deselected (they run only with an API key).

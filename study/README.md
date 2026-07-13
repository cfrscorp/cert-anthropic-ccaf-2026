# CCAF Study App

A **local, offline, single-user** study app for the Claude Certified Architect –
Foundations (CCAF) exam: a scenario **practice-question bank**, **flashcards**,
**concept explainers**, and a **readiness dashboard** that tracks your progress
over time. No cloud, no accounts, no backend — everything runs on your machine and
your progress lives in your browser.

The content is plain, schema-validated **JSON** (`data/`); the app is dependency-free
**HTML/CSS/JS** (`web/`) that reads it.

## Run it

```bash
# From the repo root — uses uv; no extra downloads (serve.py is stdlib-only):
uv run study/serve.py
```

This starts a local server and opens `http://localhost:8000/web/`. Options:

```bash
uv run study/serve.py --port 8123      # pick a port
uv run study/serve.py --no-browser     # don't auto-open
uv run study/serve.py --help
```

**Prefer a downloaded binary?** The app is just static files, so any static server
works — point it at this `study/` directory and open `/web/`:

```bash
caddy file-server --root . --listen :8000
static-web-server -d . -p 8000
miniserve . -p 8000
```

> Why a server at all? Browsers block `fetch()` of local files opened via `file://`.
> Serving over `http://localhost` fixes that and keeps the JSON as editable files.

### Share on your LAN (LAN-only)

By default the server binds to `127.0.0.1` (this machine only). To share the app with
other devices **on your local network** while keeping it **off the public internet**,
start it bound to all local interfaces on a fixed port:

```bash
uv run study/serve.py --host 0.0.0.0 --port 8000
```

**Why this stays LAN-only:** home/office routers don't forward inbound connections from
the internet by default, so this only exposes the server to devices on the same network.
Keep it that way with two rules: **(1)** never add a port-forwarding / NAT rule on your
router (and don't use a tunnel like ngrok/Cloudflare Tunnel), and **(2)** scope your OS
firewall to your *private* network (steps below). Only use this on a trusted network
(home/office) — never on public Wi‑Fi (cafés, airports, hotels, conferences).

### Local Access

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

## Features

- **Quiz** — scenario multiple-choice (the exam's format). Filter by domain / task
  statement, answer, then see the correct choice **and why each distractor is wrong**,
  with a running score and an end-of-set summary.
- **Flashcards** — click-to-flip fact recall (CLI flags, `tool_choice` values, batch
  limits, `stop_reason`, …). Filter and shuffle.
- **Concepts** — one explainer per exam task statement (1.1–5.6): the idea, why it
  matters, the common trap, and a link to the relevant hands-on lab in `../labs/`.
- **Readiness** — a cumulative dashboard: overall readiness % (weighted by the exam's
  domain weights), per-domain and per-task mastery bars, a readiness-over-time
  sparkline, and "revisit lab-NN" suggestions for weak areas.

### Progress tracking

Progress is cumulative and persists across sessions in your browser's `localStorage`
(no accounts). Because it's browser-local, a different browser/profile or clearing
site data starts fresh — use **Export** / **Import** on the Readiness view to back up
or move your progress, or **Reset** to start over.

## Content model (`data/`)

| File | What |
|------|------|
| `meta.json` | Domains + exam weights, the 30 task statements, and the task → lab map. |
| `questions.json` | Scenario multiple-choice questions (stem, 4 options, correct, per-distractor rationale, lab link). |
| `flashcards.json` | Front/back fact-recall cards. |
| `concepts.json` | One explainer per task statement. |
| `schema/*.schema.json` | JSON Schemas; every data file is validated against these. |

### Adding or editing content

Edit the JSON in `data/`, then validate:

```bash
cd study && uv run pytest
```

The tests check schema validity, integrity (valid answer keys, complete distractor
rationales, real task statements, resolvable lab links, weights summing to 100) and
coverage (question count per task statement). Coverage is gated by `PILOT_DOMAINS` in
`tests/test_study_data.py` — widen it to all five domains once every domain is authored.

# AGENTS.md

## Cursor Cloud specific instructions

CargoNext (`logistics`) is a **Frappe Framework v16 app** that depends on **ERPNext v16**. It is not a standalone service; it runs inside a Frappe **bench**.

### Where things live (already set up in the VM snapshot)
- Bench: `~/frappe-bench` (Python 3.14 virtualenv at `~/frappe-bench/env`, Node 24 for asset builds).
- This repo is symlinked into the bench as `~/frappe-bench/apps/logistics -> /workspace`, so **edits to this repo are live** in the running site (Python changes need a process reload; JS/CSS are rebuilt by the `watch` process).
- Site: `logistics.localhost` (default site). Desk URL: `http://logistics.localhost:8000` (Chrome/curl treat `*.localhost` as loopback).
- Login: `Administrator` / `admin`. MariaDB `root` password: `frappe`.
- `~/.bashrc` prepends Node 24 (`~/.nvm/versions/node/v24.18.0/bin`) and `~/.local/bin` (bench CLI) to `PATH`. Use a login shell so `bench` and Node 24 resolve.

### Starting the app (services are NOT auto-started on boot — no systemd here)
Run these in order before using the site:
```bash
sudo service mariadb start          # MariaDB (data persists in snapshot)
sudo service redis-server start     # optional; bench starts its own redis on :13000/:11000
cd ~/frappe-bench && bench start     # web (:8000), socketio (:9000), workers, redis, esbuild watch
```
`bench start` is long-running — run it in a tmux session and leave it running.

### Testing / lint
- Tests (Frappe runner): `cd ~/frappe-bench && bench --site logistics.localhost run-tests --app logistics` (or `--module <dotted.path>` for one module). The site already has `allow_tests: true`.
- No dedicated linter is configured in this repo (no ruff/eslint/pre-commit config). For a quick syntax check: `~/frappe-bench/env/bin/python -m compileall -q /workspace/logistics`.

### Non-obvious gotchas
- **Two data-seed patches fail on a fresh install/migrate** and are app-side (not environment) issues: `logistics.patches.v1_0_seed_exhibit_activity_codes` (module `Exhibits` exists on disk under `logistics/exhibits/` but is missing from `logistics/modules.txt`), and `logistics.patches.v3_0_outlook_calendar_setup` (Outlook `Connected App` link). If you ever reinstall the app or re-run migrate, use `bench --site logistics.localhost migrate --skip-failing`. Core modules (Transport, Warehousing, Customs, Freight, Job Management, etc.) are unaffected.
- Frappe v16 requires **Python 3.14** and **Node 24**; the bench `env` and `PATH` are already configured for this. Do not rebuild the bench env on the system Python 3.12.
- To reset the ERPNext setup wizard state, `System Settings.setup_complete` is the flag; a Company (e.g. `Test Company`) has already been created via the wizard on this site.

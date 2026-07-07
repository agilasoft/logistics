# AGENTS.md

## Cursor Cloud specific instructions

This repo is the **CargoNext** logistics app (`logistics`), a custom app for the **Frappe Framework v16 + ERPNext v16**. It only runs inside a Frappe *bench*. The bench is pre-provisioned in the VM snapshot at `~/frappe-bench`, with `apps/logistics` symlinked to this repo (`/workspace`), so edits here are picked up live.

Key facts:
- **Bench:** `~/frappe-bench` (Frappe v16 + ERPNext v16, Python 3.14 venv at `~/frappe-bench/env`).
- **Site:** `logistics.localhost` (default site). Admin login: `Administrator` / `admin`. MariaDB root password: `frappe`.
- **UI:** http://logistics.localhost:8000 (a `logistics.localhost` → 127.0.0.1 entry is in `/etc/hosts`). The first-run setup wizard has already been completed (Company: CargoNext).

### Starting services (must be done each session — no systemd auto-start)
Services do not auto-start. Start the database first, then the bench dev stack:
```bash
sudo service mariadb start            # MariaDB (required, must be up before bench)
cd ~/frappe-bench && bench start      # web :8000, socketio :9000, its own Redis (:11000/:13000), workers, scheduler, asset watcher
```
`bench start` launches Frappe's own Redis instances and the JS/CSS watcher; you do NOT need the system `redis-server`. Run `bench start` in a long-lived tmux session (it is a foreground dev server — never put it in the update script).

### Node version gotcha (non-obvious)
Frappe v16 requires **Node >= 24**, but a `node` v22 shim on `PATH` at `/exec-daemon/node` shadows nvm. `~/.bashrc` prepends the nvm Node 24 bin dir so login shells get Node 24 (needed for `yarn`, `bench build`, and the asset watcher). If yarn/asset builds fail with an "engine node incompatible, Expected >=24" error, you are using the wrong Node — start a fresh login shell (`bash -l`) so the bashrc fix applies.

### Syncing DocTypes after code/app changes (non-obvious)
After pulling new app code or changing DocType JSONs, run a migrate (and clear cache) so the DB schema/metadata matches the code — a DocType can 404 in the UI until this is done:
```bash
cd ~/frappe-bench && bench --site logistics.localhost migrate && bench --site logistics.localhost clear-cache
```

### Tests
Test execution is enabled for the site (`allow_tests` is set). Run the app suite or a single module:
```bash
cd ~/frappe-bench
bench --site logistics.localhost run-tests --app logistics
bench --site logistics.localhost run-tests --module logistics.air_freight.utils.test_unlocode_utils
```

### Lint
No formal linter is configured in this repo (no ruff/flake8/pre-commit/eslint config). A quick sanity check is `~/frappe-bench/env/bin/python -m compileall logistics` (pre-existing `SyntaxWarning: invalid escape sequence` messages are harmless).

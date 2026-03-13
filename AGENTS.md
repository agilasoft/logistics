# CargoNext (Logistics Management System)

A comprehensive logistics management system built as a Frappe Framework app.

## Cursor Cloud specific instructions

### Architecture

- **Frappe App** (`logistics`) installed on a Frappe Bench with ERPNext v16+ as a dependency.
- Tech stack: Python 3.14, Frappe v16, ERPNext v16, MariaDB, Redis (3 instances), Node.js 24+.
- The workspace at `/workspace` is symlinked into `/home/ubuntu/frappe-bench/apps/logistics`.

### Starting services

All services are managed via `bench start` from `/home/ubuntu/frappe-bench`:

```bash
export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm use 24
cd /home/ubuntu/frappe-bench
# Ensure MariaDB is running
sudo mysqld_safe &
sleep 3
# Start all Frappe services (Redis, web server, socketio, workers, file watcher)
bench start
```

The dev server runs on `http://localhost:8000`. Default login: `Administrator` / `admin`.

### Running tests

```bash
cd /home/ubuntu/frappe-bench
bench --site logistics.localhost run-tests --app logistics
# Or run a specific test module:
bench --site logistics.localhost run-tests --module "logistics.logistics.doctype.consignee.test_consignee"
```

**Note:** Tests require `allow_tests` to be enabled (`bench --site logistics.localhost set-config allow_tests true`). Some tests may fail due to missing DocType JSON definitions (e.g., `Air Booking Charges`) — this is a pre-existing codebase issue.

### Linting

No project-specific linter config exists. Use `ruff` (installed in bench venv):

```bash
cd /workspace
/home/ubuntu/frappe-bench/env/bin/ruff check logistics/
```

### Build

```bash
cd /home/ubuntu/frappe-bench
bench build --app logistics
```

### Key gotchas

- **Node.js 24+ required**: Frappe v16 enforces `engines.node >= 24` in its `package.json`. Node 22 will fail `yarn install`.
- **Python 3.14 required**: The `pyproject.toml` specifies `requires-python = ">=3.14,<3.15"`. Install via deadsnakes PPA.
- **MariaDB must be started manually** in the cloud VM since systemd isn't fully available. Use `sudo mysqld_safe &`.
- **Redis ports**: `bench start` manages its own Redis instances on ports 13000 (cache/socketio) and 11000 (queue). Stop any manually started Redis on those ports before running `bench start`.
- **The logistics app is symlinked**: `/home/ubuntu/frappe-bench/apps/logistics -> /workspace`. After pulling new code, run `uv pip install -e /workspace --python /home/ubuntu/frappe-bench/env/bin/python` then `bench --site logistics.localhost migrate` to apply schema changes.
- **Site name**: `logistics.localhost` (set as default site).

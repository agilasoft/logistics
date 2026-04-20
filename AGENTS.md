# AGENTS.md

## Cursor Cloud specific instructions

### Project Overview
CargoNext is a comprehensive logistics management system built as a **Frappe Framework v16 app** (`logistics`) on top of ERPNext v16. See `README.md` for full feature list.

### Development Environment Layout
- **Frappe bench**: `/home/ubuntu/frappe-bench`
- **Logistics app**: symlinked at `/home/ubuntu/frappe-bench/apps/logistics` -> `/workspace`
- **Python venv**: `/home/ubuntu/frappe-bench/env` (Python 3.14)
- **Site**: `cargonext.localhost` (admin password: `admin123`)
- **Node.js 24** is required (Frappe v16 mandates `>=24`). Use `nvm use 24` before bench commands.

### Starting Services
Before running `bench start`, stop any manually-started Redis instances that may occupy ports 11000/13000 (bench manages its own Redis). If bench fails with "Address already in use" for Redis, run:
```bash
redis-cli -p 11000 shutdown 2>/dev/null; redis-cli -p 13000 shutdown 2>/dev/null
```

Start all services:
```bash
source /home/ubuntu/.nvm/nvm.sh && nvm use 24
cd /home/ubuntu/frappe-bench
sudo service mariadb start
bench start
```
The dev server runs at `http://localhost:8000`.

### Running Tests
```bash
cd /home/ubuntu/frappe-bench
bench --site cargonext.localhost run-tests --app logistics
```
Testing must be enabled on the site (`allow_tests` is already set to `true`). To run a specific module:
```bash
bench --site cargonext.localhost run-tests --app logistics --module "logistics.job_management.tests.test_recognition_engine"
```

### Linting
No project-specific linting config exists. Use `ruff` (installed globally):
```bash
ruff check /workspace/logistics/ --select E,F
```

### Building Assets
After modifying JS/CSS files in the logistics app:
```bash
source /home/ubuntu/.nvm/nvm.sh && nvm use 24
cd /home/ubuntu/frappe-bench && bench build --app logistics
```

### Key Gotchas
- The Procfile socketio path references a specific Node.js version path. If you upgrade Node.js, update the `socketio` line in `/home/ubuntu/frappe-bench/Procfile`.
- Some test modules (e.g. `test_recognition_engine.TestRecognitionEngine`) require ERPNext Company data to be set up first. Run `bench --site cargonext.localhost execute erpnext.setup.utils.before_tests` if tests fail with missing Company errors.
- The `pyproject.toml` declares `requires-python = ">=3.14,<3.15"`. Python 3.14 is installed from `ppa:deadsnakes/nightly`.

# Cloud Agent Guide for CargoNext (Logistics)

## Environment Overview

This is a Frappe/ERPNext application. The development environment includes:

- **Frappe Framework v16** - Python web framework
- **ERPNext v16** - Business management software
- **Python 3.11** - Runtime environment
- **MariaDB** - Database server
- **Redis** - Cache and queue server
- **Node.js 18** - Frontend build tools

## Environment Structure

```
/home/ubuntu/frappe-bench/          # Frappe bench directory
├── apps/
│   ├── frappe/                     # Frappe Framework
│   ├── erpnext/                    # ERPNext application
│   └── logistics/                  # Logistics app (symlinked from /workspace)
├── env/                            # Python virtual environment
├── sites/
│   └── development.localhost/      # Development site
└── config/                         # Bench configuration
```

```
/workspace/                         # Git repository (logistics app)
```

## Development Workflow

### Starting the Development Server

```bash
cd /home/ubuntu/frappe-bench
bench start
```

This starts:
- Web server on port 8000
- Socket.io server on port 9000
- Redis queue workers
- Redis cache server
- Redis socketio server

### Running Tests

```bash
cd /home/ubuntu/frappe-bench
bench --site development.localhost run-tests --app logistics
```

### Database Migrations

After making changes to DocTypes or database schema:

```bash
cd /home/ubuntu/frappe-bench
bench --site development.localhost migrate
```

### Clearing Cache

```bash
cd /home/ubuntu/frappe-bench
bench --site development.localhost clear-cache
```

### Reinstalling the App

If you need to reinstall the logistics app:

```bash
cd /home/ubuntu/frappe-bench
bench --site development.localhost uninstall-app logistics
bench --site development.localhost install-app logistics
```

### Building Frontend Assets

After modifying JavaScript, CSS, or other frontend files:

```bash
cd /home/ubuntu/frappe-bench
bench build --app logistics
```

## Working with Code

### Making Changes

The logistics app code is in `/workspace` (the git repository). Changes made here are immediately reflected because it's symlinked to `/home/ubuntu/frappe-bench/apps/logistics`.

### Installing Python Dependencies

If you add dependencies to `pyproject.toml`:

```bash
cd /home/ubuntu/frappe-bench
./env/bin/pip install -e apps/logistics
```

### Console Access

To access the Frappe console for debugging:

```bash
cd /home/ubuntu/frappe-bench
bench --site development.localhost console
```

## Testing Changes

### Manual Testing

1. Start the development server: `cd /home/ubuntu/frappe-bench && bench start`
2. Access the web interface at `http://localhost:8000`
3. Login with:
   - Username: `Administrator`
   - Password: `admin`
4. Test your changes through the web interface

### Automated Testing

Run tests for specific modules:

```bash
cd /home/ubuntu/frappe-bench
bench --site development.localhost run-tests --app logistics --module logistics.logistics.doctype.transport_order
```

## Common Issues

### MariaDB Not Running

```bash
sudo systemctl start mariadb
```

### Redis Not Running

```bash
sudo systemctl start redis-server
```

### Port Already in Use

If port 8000 is in use, you can stop all bench processes:

```bash
cd /home/ubuntu/frappe-bench
bench stop
```

### Database Connection Issues

Check MariaDB status:

```bash
sudo systemctl status mariadb
```

### Cache Issues

Clear all caches:

```bash
cd /home/ubuntu/frappe-bench
bench --site development.localhost clear-cache
bench --site development.localhost clear-website-cache
```

## Cursor Cloud Specific Instructions

### Environment Setup

The environment is automatically set up from `.cursor/environment.json`. If you need to rebuild:

1. The install script takes approximately 10-15 minutes
2. It installs all system dependencies, Frappe, ERPNext, and the logistics app
3. A development site is created at `development.localhost`

### Testing in Cloud Agents

When making changes:

1. **Backend changes** (Python files): Restart bench or use `bench restart`
2. **Frontend changes** (JS/CSS): Run `bench build --app logistics`
3. **DocType changes**: Run `bench migrate`
4. **Always test manually** through the web interface using the `computerUse` subagent

### Credentials

- **Site**: `development.localhost`
- **Admin Username**: `Administrator`
- **Admin Password**: `admin`
- **MariaDB Root Password**: `admin`

## Architecture Notes

### DocTypes

Frappe uses DocTypes as the data model. Each DocType is defined in JSON files and has associated Python controllers.

Key DocTypes in logistics:
- Transport Order
- Transport Job
- Warehouse Job
- Sales Quote
- Time Sensitive Case
- And many more...

### Hooks

The app's hooks are defined in `logistics/hooks.py`. This configures:
- App metadata
- Fixtures
- Scheduled jobs
- Web routes
- Event handlers
- Permission queries

### Portals

The app provides portal pages for external users:
- `/warehousing-portal` - Warehouse job access
- `/transport-jobs` - Transport job tracking
- `/stock-balance` - Stock balance queries
- `/warehouse-jobs` - Warehouse job details

## Additional Resources

- [Frappe Framework Documentation](https://frappeframework.com/docs)
- [ERPNext Documentation](https://docs.erpnext.com/)
- [Bench CLI Documentation](https://github.com/frappe/bench)

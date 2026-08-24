# Project Instructions

## Tech Stack
- **Agent**: Python (PyInstaller built `.exe`), `win32api`, `websockets`
- **Backend API**: Python, FastAPI, SQLAlchemy, PostgreSQL, Alembic, PyJWT
- **Manager Web**: React 19, Vite 8, TailwindCSS 4, Lucide React, Oxlint

## Code Style
- **Python (Agent & Backend)**: standard snake_case for functions/variables, PascalCase for classes.
- **React (Manager Web)**: camelCase for variables, PascalCase for components.
- Use `oxlint` for linting in `manager-web`.

## Testing
- **Backend**: Uses `pytest`. Run tests via `pytest` (e.g. `test_phase1.py`).
- **Agent**: Test files like `test_phase2_agent.py`, `test_system_integrity.py`.

## Build & Run
- **Agent Build**: `build_and_pack_agent.bat` or `build_prod_exe.bat`
- **Agent Run**: `start_agent.bat`
- **Backend Run**: `run_backend.bat` (uvicorn)
- **Web Manager Dev**: `cd manager-web && npm run dev`
- **Web Manager Build**: `cd manager-web && npm run build`
- **Docker**: `docker-compose up` for overall orchestration.

## Project Structure
- `agent/`: Python Agent for Windows (locking, taking screenshots, tracking usage).
- `backend_api/`: FastAPI server processing requests, storing logs and settings.
- `manager-web/`: Vite + React dashboard for managing the devices.
- `shared/`: Shared resources/configs.

## Conventions
- **Error Handling**: Standard try/catch/except.
- **Data Flow**: Agent polls Backend -> Backend updates Postgres -> Web fetches from Backend.

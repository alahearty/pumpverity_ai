# Local infrastructure

The Docker Compose development stack provides:

- `api` — FastAPI/Uvicorn on port 8000, SQLite data in the shared `pumpverity-data` volume.
- `mcp` — official-SDK FastMCP Streamable HTTP server on internal port 8010.
- `web` — Vite development server on port 5173, proxying `/api` to the API service.

The API container runs Alembic migrations and idempotent reference/demo-user seeding before
serving requests. The demo password must be supplied through `PETROSENSE_DEMO_PASSWORD`; it is
never embedded in an image or committed to the repository.

```powershell
Copy-Item .env.example .env
# Replace the secret and demo password in .env
docker compose up --build
```

Open `http://localhost:5173`. The API documentation is at `http://localhost:8000/docs`. The MCP
endpoint is internal to the Compose network (`http://mcp:8010/mcp`) and uses the same API secret as
a service-token fallback.

Changing `PETROSENSE_DEMO_PASSWORD` does not rewrite existing local accounts. To reset the four
demo accounts in a container, run:

```powershell
docker compose exec api python -m app.db.seed --reset-passwords
```

Production deployment, TLS termination, PostgreSQL and physical edge-device deployment are out of
scope for this research prototype.


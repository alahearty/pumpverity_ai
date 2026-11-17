# Shared contracts

TypeScript domain enums and API DTOs used by the PUMPVERITY AI web client. The Python
Pydantic/OpenAPI contracts in `apps/api` remain authoritative; this package carries the
hand-maintained subset needed by the SPA and is versioned alongside the API.

Status: Stage 1 foundation. Generate client types from OpenAPI in a later stage if the
contract grows beyond a manageable hand-maintained subset.

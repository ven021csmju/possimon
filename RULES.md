# RULES.md — PoSimon Backend Development Rules

## Coding Standards

### Python
- Follow **PEP 8** — 4 spaces, no tabs
- Max line length: **120 characters**
- Use **type hints** on all function signatures
- No commented-out code — delete it
- No `print()` in production — use logging if needed

### Imports
- Group: stdlib → 3rd party → internal (one blank line between groups)
- Always absolute: `import models` not `from . import models`
- Prefer module-level: `import crud`, `import schemas`

### SQLAlchemy
- All models in `models/__init__.py`
- Use `relationship()` + `back_populates` (not `backref`)
- `with_for_update()` for stock-sensitive transactions
- Commit only in services, not in CRUD (except simple single-row ops)

### Pydantic
- Pydantic v2 — use `model_dump()` not `.dict()`
- ORM mode: `from_attributes = True`
- Use `Field(...)` for validation constraints

### API Design
- Plural nouns for endpoints: `/products`, `/orders`
- POST = create, GET = read, PUT/PATCH = update, DELETE = delete
- Pagination via `skip`/`limit` Query params where needed
- Role-based access via `RoleChecker` dependency

## Git Conventions

### Branch Naming
```
feature/<short-description>    # New feature
fix/<short-description>        # Bug fix
refactor/<short-description>   # Refactoring
chore/<short-description>      # Build, config, tooling
docs/<short-description>       # Documentation
```

### Commit Messages
```
type: concise description

- type: feat, fix, refactor, chore, docs, test, style
- Present tense: "add" not "added"
- Capitalize first letter: "Add login endpoint"
- No period at end
```

### What NOT to Commit
- `.env` files (secrets)
- `__pycache__/`, `*.pyc`
- `*.db`, `*.sqlite3`
- IDE files (`.vscode/`, `.idea/`)
- API keys, tokens, passwords

## Code Review Rules
1. No business logic in routers — delegate to services or CRUD
2. No raw SQL unless absolutely necessary
3. Every new endpoint needs role/permission check
4. Stock mutations must use `with_for_update()` inside a try/commit/rollback block
5. No `except: pass` — always handle or re-raise
6. Schema `Out` classes must have `from_attributes = True`

## Testing
- Core business logic in `services/` should be testable
- Use `test_concurrency.py` as reference for concurrency tests
- Run locally with SQLite before committing

## Security
- Passwords hashed via `pbkdf2_sha256` (passlib)
- JWT tokens expire in 2 hours
- CORS restricted to `ALLOWED_ORIGINS`
- Session cookie signed via `SECRET_KEY`

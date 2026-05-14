# PoSimon Backend

Backend API for PoSimon POS system — wine & product management, order processing, payment handling with PromptPay QR, and multi-provider OAuth login.

## Tech Stack

| Category | Technology |
|----------|-----------|
| Framework | FastAPI (Python 3.10+) |
| ORM | SQLAlchemy |
| Database | PostgreSQL (production) / SQLite (local) |
| Migration | Alembic |
| Auth | JWT (python-jose), OAuth 2.0 (Google, LINE, Facebook) |
| Payment | PromptPay QR (qrcode + Pillow) |
| Server | Uvicorn (dev) / Gunicorn (production) |
| Deploy | Render |

## Quick Start

```bash
# Clone & enter
git clone <repo-url> && cd PoSimon_backend

# Install dependencies
pip install -r requirements.txt

# Create .env (see below)
# Run
uvicorn main:app --reload
```

### Environment Variables (`.env`)

```env
DATABASE_URL=sqlite:///./test.db
SECRET_KEY=your_secret_key
ALLOWED_ORIGINS=https://the-bottel-club-premium.vercel.app,http://localhost:3000,http://localhost:5173
FRONTEND_URL=https://the-bottel-club-premium.vercel.app/auth/success

# OAuth (optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
LINE_CHANNEL_ID=
LINE_CHANNEL_SECRET=
FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=
```

## Project Structure

```
├── main.py                  # FastAPI app entry point
├── database.py              # SQLAlchemy engine & session
├── alembic/                 # DB migrations
├── models/                  # ORM models (single __init__.py)
├── schemas/                 # Pydantic schemas (single __init__.py)
├── crud/                    # Data access layer
├── services/                # Business logic layer
│   ├── order_service.py     # Order with stock locking
│   ├── payment_service.py   # Payment + WebSocket broadcast
│   └── qr_service.py        # PromptPay QR generation
├── routers/                 # API endpoints
│   ├── auth.py              # Login, register, OAuth
│   ├── products.py          # Product CRUD
│   ├── orders.py            # Order CRUD
│   ├── users.py             # User address CRUD
│   ├── payments.py          # QR + payment confirmation
│   ├── wines.py             # Wine catalog CRUD
│   └── websocket.py         # Real-time WebSocket
├── auth/                    # JWT, OAuth, dependencies
└── core/                    # Config & security
```

## API Endpoints

### Auth (`/api/auth`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/login` | Username/password login |
| POST | `/register` | Register new user |
| GET | `/login/google/web` | Google OAuth (Web) |
| GET | `/login/google/pos` | Google OAuth (POS) |
| GET | `/login/line/web` | LINE OAuth (Web) |
| GET | `/login/line/pos` | LINE OAuth (POS) |
| GET | `/login/line` | LINE OAuth |
| GET | `/login/facebook` | Facebook OAuth |

### Products (`/api/products`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/products` | - | List all |
| POST | `/products` | admin/manager | Create |

### Orders (`/api/orders`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/orders` | any | Create (stock locking) |
| GET | `/orders` | admin/manager/cashier | List all |
| GET | `/orders/{id}` | owner/admin | Get by ID |

### Users (`/api/users`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/users/addresses` | any | Add address |
| GET | `/users/{id}/addresses` | owner/admin | List addresses |

### Payments (`/api/payments`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/generate-qr` | any | Get PromptPay QR |
| POST | `/confirm-payment/{order_id}` | any | Confirm payment |

### Wines (`/api/wines`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/wines` | - | List wines |
| POST | `/wines` | admin | Create wine |
| GET | `/wines/countries` | - | List countries |
| POST | `/wines/countries` | admin | Create country |
| GET | `/wines/regions` | - | List regions |
| POST | `/wines/regions` | admin | Create region |
| GET | `/wines/wineries` | - | List wineries |
| POST | `/wines/wineries` | admin | Create winery |
| GET | `/wines/grapes` | - | List grapes |
| POST | `/wines/grapes` | admin | Create grape |
| POST | `/wines/ratings` | admin | Add rating |
| GET | `/wines/{id}/ratings` | - | Get ratings |

### WebSocket (`/api/ws`)
| Path | Description |
|------|-------------|
| `/ws` | Real-time payment notifications |

## Data Flow

```
Router (HTTP) → Service (business logic) → CRUD (DB queries) → Model (ORM)
                                                              ↕
                                                           Database
```

### Order Flow (with stock locking)
1. Validate address (online orders)
2. Lock product rows (`SELECT ... FOR UPDATE`)
3. Validate stock availability
4. Create order + order items
5. Deduct stock
6. Create payment record
7. Commit transaction

## Seeding

On startup, `main.py` auto-seeds via `seed.py`:
- **Users**: admin, john_doe
- **Products**: Coke, Pepsi, Water
- **Wine catalog**: France/Italy, Bordeaux/Tuscany, Château Margaux/Antinori, Cabernet Sauvignon/Merlot, 2 wines

## Deployment

Deployed on Render via `render.yaml`. Build & start:

```yaml
buildCommand: pip install -r requirements.txt
startCommand: gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:$PORT
```

## Scripts

| Script | Purpose |
|--------|---------|
| `seed.py` | Seed development data |
| `migrate_db.py` | Database migration helper |
| `refill_stock.py` | Restock products |
| `import_csv.py` | Bulk CSV import |
| `test_concurrency.py` | Concurrency tests |

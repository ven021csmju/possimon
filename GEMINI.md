# PoSimon Backend - Project Documentation

## 🚀 Overview
PoSimon Backend is a FastAPI-based system designed to handle Point of Sale (POS) and Online orders for a wine and product retail business. It features multi-frontend support (Web & POS), social authentication, and robust order management.

## 🛠 Tech Stack
- **Framework:** FastAPI (Python)
- **ORM:** SQLAlchemy
- **Database:** SQLite (Current), support for PostgreSQL
- **Auth:** Authlib (Google, LINE, Facebook OAuth), JWT for sessions
- **Deployment:** Render (Backend), Vercel (Frontends)

---

## 🏗 Current Capabilities (Detailed)

### 1. Authentication & Security
- **Multi-Provider OAuth:** Fully integrated Google, LINE, and Facebook login.
- **Fixed Google OAuth Flow:** 
    - Resolved `mismatching_state` (CSRF) errors by optimizing middleware order and using `SameSite="none"`.
    - Fixed `coroutine` errors in the Google callback logic.
    - Added support for multiple frontend sources via `state` parameter (Web vs. POS).
- **Session Management:** Secure HttpOnly cookies for JWT tokens.
- **Role-Based Access Control (RBAC):** Roles including `admin`, `manager`, `cashier`, and `customer`.

### 2. Order Management
- **Unified Order System:** Handles both `POS` and `ONLINE` order types.
- **Atomic Transactions:** Uses database locking (`with_for_update`) to prevent stock race conditions during high-concurrency order creation.
- **Inventory Integration:** Automatically deducts stock upon order placement and validates availability.
- **Pricing Logic:** Dynamically uses `selling_price` with a fallback to base `price`.

### 3. Product & Wine Management
- **Polymorphic Models:** Specialized `Wine` model extending the base `Product` model.
- **Detailed Wine Metadata:** Supports designation, winery, region, country, vintage, alcohol content, and grape varieties.
- **Rating System:** Ability to store scores and reviews for wines.
- **Image Management:** Multi-image support per product with physical file storage tracking.

### 4. Database & Infrastructure
- **Migrations:** Managed via Alembic for versioned schema updates.
- **CORS Configuration:** Configured to allow multiple Vercel and Localhost origins.
- **Proxy Handling:** Custom middleware to recognize HTTPS headers from Render's proxy.

---

## 📡 API Endpoints (Highlights)

### Auth
- `GET /api/auth/google`: Start Google Login (Supports `?source=web` or `?source=pos`).
- `GET /api/auth/google/callback`: Secure callback handler.
- `POST /api/auth/login`: Traditional username/password login.
- `GET /api/auth/me`: Get current user profile.

### Orders
- `POST /api/orders`: Create a new order (Atomic stock check).
- `GET /api/orders`: List all orders (Admin/Staff only).
- `GET /api/orders/{id}`: Detailed order view.

### Products/Wines
- `GET /api/products`: List all products.
- `GET /api/wines`: Specialized wine search and listing.

---

## ⚙️ Configuration (Environment Variables)
- `DATABASE_URL`: Connection string for the database.
- `WEB_FRONTEND_URL`: `https://front-posimon.vercel.app/auth/success`
- `POS_FRONTEND_URL`: `https://front-posimon.vercel.app/auth/success`
- `COOKIE_SAMESITE`: Set to `none` for cross-domain OAuth support.

## 📝 Recent Fixes & Updates
- **2024-05-19:**
    - Refactored `main.py` middleware to fix `ProxyHeaders` and `SessionMiddleware` sequence.
    - Updated `routers/auth.py` to fix async/await bug in Google callback.
    - Pointed all production redirects to Vercel URLs.
    - Added `/api/auth/google` alias to simplify frontend integration.

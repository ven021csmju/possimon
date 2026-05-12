import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from database import Base, SessionLocal, engine
from seed import seed_data
from core.config import settings
from core.logging_config import setup_logging
from routers import auth, products, orders, users, payments, wines, websocket, employees, customers

# Initialize logging
logger = setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION
)

# Middleware
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
)

# Startup event
@app.on_event("startup")
def startup_event():
    logger.info("Starting up the application...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_data(db)
        logger.info("Database seeded successfully.")
    except Exception as e:
        logger.error(f"Error during startup seeding: {e}")
    finally:
        db.close()

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )

# Static/Legal Routes
@app.get("/privacy", response_class=HTMLResponse)
def privacy():
    return """
    <h1>Privacy Policy</h1>
    <p>This app collects name and email for login.</p>
    <p>We do not share your data.</p>
    <p>Contact: venn0217@gmail.com</p>
    """

@app.get("/data-deletion", response_class=HTMLResponse)
def delete():
    return """
    <h1>Data Deletion Instructions</h1>
    <p>If you want to delete your data, please contact us:</p>
    <ul>
        <li>Email: venn0217@gmail.com</li>
    </ul>
    <p>We will process your request within 7 days.</p>
    """

@app.get("/terms", response_class=HTMLResponse)
def terms():
    return """
    <h1>Terms of Service</h1>
    <p>By using this app, you agree to our terms.</p>
    """

# Include Routers
app.include_router(auth.router, prefix="/api/auth")
app.include_router(employees.router, prefix="/api")
app.include_router(customers.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(payments.router, prefix="/api/payments")
app.include_router(wines.router, prefix="/api/wines")
app.include_router(websocket.router, prefix="/api")


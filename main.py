import os
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from database import Base, SessionLocal, engine
from database_nosql import create_mongo_indexes, db as mongo_db
from core.minio_client import init_minio
from seed import seed_data
from core.config import settings
from core.logging_config import setup_logging
from routers import auth, products, orders, users, payments, wines, employees, customers, product_images, reviews
from websocket import router as websocket_router

from exceptions.handler import register_exception_handlers
from core.logging_config import logger as app_logger

# Initialize logging
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION
)

# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    app_logger.info(f"Incoming request: method={request.method} path={request.url.path}")
    response = await call_next(request)
    app_logger.info(f"Request completed: method={request.method} path={request.url.path} status_code={response.status_code}")
    return response

# Register exception handlers
register_exception_handlers(app)

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Static Files
app.mount(settings.STATIC_URL_PREFIX, StaticFiles(directory=settings.UPLOAD_DIR), name="static")

# Middleware
class ProxyHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            # x-forwarded-proto is usually in bytes in the scope headers
            proto = None
            for k, v in scope.get("headers", []):
                if k.lower() == b"x-forwarded-proto":
                    proto = v.decode("utf-8")
                    break
            
            if proto:
                scope["scheme"] = proto
        
        await self.app(scope, receive, send)

# Add middlewares in order (Last added = Outermost)
app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.SECRET_KEY,
    https_only=True,
    same_site="none" # Changed from "lax" to "none" for cross-site redirects
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ProxyHeadersMiddleware)

# Startup event
@app.on_event("startup")
async def startup_event():
    app_logger.info("Starting up the application...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_data(db)
        app_logger.info("Database seeded successfully.")
    except Exception as e:
        app_logger.error(f"Error during startup seeding: {e}")
    finally:
        db.close()

    try:
        await create_mongo_indexes()
        app_logger.info("MongoDB indexes created successfully.")
    except Exception as e:
        app_logger.error(f"Error creating MongoDB indexes: {e}")

    try:
        init_minio()
        app_logger.info("MinIO initialized successfully.")
    except Exception as e:
        app_logger.error(f"Error initializing MinIO: {e}")

# Root / Health Check
@app.get("/")
def health_check():
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

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

@app.get("/test-mongodb")
async def root():
    if mongo_db is None:
        return JSONResponse(
            status_code=503,
            content={"message": "MongoDB is not configured"}
        )
    try:
        collections = await mongo_db.list_collection_names()
        return {
            "message": "MongoDB Connected",
            "collections": collections
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"MongoDB Error: {str(e)}"}
        )


# Include Routers
app.include_router(auth.router, prefix="/api/auth")
app.include_router(employees.router, prefix="/api")
app.include_router(customers.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(product_images.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(payments.router, prefix="/api/payments")
app.include_router(wines.router, prefix="/api/wines")
app.include_router(websocket_router)
app.include_router(reviews.router)

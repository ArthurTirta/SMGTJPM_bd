"""
FastAPI Application for Jeans Product Database with AI Chat
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.main import router as ai_router
from app.api.products import router as products_router
from app.database import engine, Base
from app.core.config import settings

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered API for querying jeans product database",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ai_router, prefix=f"{settings.API_V1_STR}/ai", tags=["AI"])
app.include_router(products_router, prefix=f"{settings.API_V1_STR}/products", tags=["Products"])


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Jeans Product AI API",
        "docs": f"{settings.API_V1_STR}/docs",
        "health": "/health"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "fastapi_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

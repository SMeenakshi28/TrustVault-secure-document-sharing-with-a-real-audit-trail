import os
from app.auth import create_development_owner, users
# ------ For local testing only -------

from app.routes import router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="TrustVault API",
    description="Secure document sharing with a real audit trail",
    version="1.0.0",
)

# Temporary local-development owner account.
if os.getenv("TRUSTVAULT_CREATE_TEST_OWNER") == "true":
    email = "owner@test.com"

    if email not in users:
        create_development_owner(
            "Test Owner",
            email,
            "OwnerPass123!",
        )
        
app.include_router(router)

# Temporary CORS configuration for local development.
# We will adjust this when connecting the React frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Welcome to TrustVault API",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "TrustVault backend",
    }

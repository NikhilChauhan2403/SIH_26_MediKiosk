from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from .database import init_db
from .seed import seed_database
from .routers import (
    auth_routes,
    consent_routes,
    interview_routes,
    document_routes,
    summary_routes,
    doctor_routes,
    his_routes,
    patient_routes,
    session_routes
)

app = FastAPI(
    title="MediKiosk: AI Clinical History & Patient Case-Taking Platform",
    description="Smart AI-assisted Clinical History Software for SIH 2026 (Problem Statement SIH26047 - Ministry of Ayush / AIIA)",
    version="1.0.0"
)

# CORS setup for kiosk tablets and hospital workstations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routers
app.include_router(auth_routes.router)
app.include_router(consent_routes.router)
app.include_router(interview_routes.router)
app.include_router(document_routes.router)
app.include_router(summary_routes.router)
app.include_router(doctor_routes.router)
app.include_router(his_routes.router)
app.include_router(patient_routes.router)
app.include_router(session_routes.router)

# Health Check
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "MediKiosk AI Backend",
        "sih_problem": "SIH26047",
        "ayush_aiia_ready": True
    }

# Mount Frontend static files
STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def serve_frontend_root():
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "MediKiosk API is operational. Frontend index.html not found."}

@app.on_event("startup")
def startup_event():
    init_db()
    # Seed on startup if database is fresh
    seed_database()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)

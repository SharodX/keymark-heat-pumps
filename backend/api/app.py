"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import measurements
from backend.api.routes import heat_pumps
from backend.api.routes import en14825
from backend.api.routes import heat_pump_detail

app = FastAPI(title="Keymark Heat Pumps API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(measurements.router, prefix="/measurements", tags=["measurements"])
app.include_router(heat_pumps.router, prefix="/heat-pumps", tags=["heat-pumps"])
app.include_router(en14825.router, prefix="/en14825", tags=["en14825"])
app.include_router(heat_pump_detail.router)


@app.get("/health", tags=["health"])
def healthcheck() -> dict[str, str]:
    """Simple health endpoint for uptime probes."""
    return {"status": "ok"}

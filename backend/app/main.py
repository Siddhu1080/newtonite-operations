
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import work_items
from app.routers import auth
from app.routers import teams
from app.routers import comments
from app.routers import activities

app = FastAPI(
    title="Newtonite Operations API",
    description="API for managing internal operational work items",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(work_items.router)
app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(comments.router)
app.include_router(activities.router)

@app.get("/")
def read_root():
    return {"message": "Newtonite Operations API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}

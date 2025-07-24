"""
Main FastAPI application for the code review backend.
"""
from fastapi import FastAPI
from routes.pr import router as pr_router

app = FastAPI(
    title="Code Review Agent",
    description="Backend service for analyzing GitHub Pull Requests",
    version="1.0.0"
)

# Include PR routes
app.include_router(pr_router, prefix="/api/v1", tags=["Pull Requests"])

@app.get("/")
async def root():
    return {"message": "Code Review Agent API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

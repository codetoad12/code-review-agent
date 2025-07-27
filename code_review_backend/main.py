"""
Main FastAPI application for the code review backend.
"""
from fastapi import FastAPI
from routes.pr import router as pr_router

app = FastAPI(
    title="Code Review Agent",
    description="Backend service for analyzing GitHub Pull Requests asynchronously",
    version="1.0.0"
)

# Include PR routes
app.include_router(pr_router, prefix="/api/v1", tags=["Pull Requests"])

@app.get("/")
async def root():
    return {
        "message": "Code Review Agent API is running",
        "endpoints": {
            "analyze_pr": "POST /api/v1/analyze-pr",
            "get_status": "GET /api/v1/status/<task_id>",
            "get_results": "GET /api/v1/results/<task_id>"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment monitoring."""
    return {"status": "healthy", "service": "code-review-agent"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

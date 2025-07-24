"""
This file contains the routes for Pull Requests.
"""
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from celery.result import AsyncResult
from handlers.pr_handlers import GithubPrHandler

class AnalyzePRRequest(BaseModel):
    repo_owner: str
    repo_name: str
    pr_number: int
 

router = APIRouter()

@router.post("/analyze_pr")
async def analyze_pr(request: AnalyzePRRequest):
    """
    Analyze a Pull Request.
    """
    print(request.__dict__)
    github_pr_handler = GithubPrHandler(request.repo_owner, 
                                        request.repo_name, 
                                        request.pr_number)
    pr_info = github_pr_handler.get_pr_info()
    return {"message": "Pull Request analyzed successfully", 
            "pr_info": pr_info}



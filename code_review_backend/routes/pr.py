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
    final_payload = github_pr_handler.format_pr_data_to_pass_to_agent()
    return {"message": "Pull Request analyzed successfully", 
            "final_payload": final_payload}



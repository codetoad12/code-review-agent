"""
This file contains the routes for Pull Requests.
"""
import os
import traceback

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from handlers.pr_handlers import GithubPrHandler
from agents.base_agent import BaseAgent

class AnalyzePRRequest(BaseModel):
    repo_owner: str
    repo_name: str
    pr_number: int
 

router = APIRouter()

@router.post('/analyze_pr')
async def analyze_pr(request: AnalyzePRRequest):
    """
    Analyze a Pull Request synchronously and return results immediately.
    """
    try:
        # Get PR data from GitHub
        github_pr_handler = GithubPrHandler(request.repo_owner, 
                                            request.repo_name, 
                                            request.pr_number)
        final_payload = github_pr_handler.format_pr_data_to_pass_to_agent()
        
        # Initialize the BaseAgent with the PR data
        agent = BaseAgent(final_payload=final_payload)
        
        # Perform the analysis synchronously
        analysis_result = agent.review()
        
        return {
            'message': 'PR analysis completed',
            'status': 'completed',
            'results': analysis_result
        }
        
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, 
            detail=f'Failed to analyze PR: {str(e)}'
        )



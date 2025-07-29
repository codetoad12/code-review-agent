"""
This file contains the routes for Pull Requests.
"""
import os
import traceback
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from celery.result import AsyncResult
from celery.exceptions import NotRegistered
from tasks import analyze_pr_task
from celery_app import celery_app


class AnalyzePRRequest(BaseModel):
    repo_url: str
    pr_number: int
    github_token: Optional[str] = None
 

router = APIRouter()


def parse_github_repo_url(repo_url: str) -> tuple[str, str]:
    """
    Parse GitHub repository URL to extract owner and repository name.
    
    Args:
        repo_url: GitHub repository URL (e.g., 'https://github.com/user/repo')
        
    Returns:
        Tuple of (repo_owner, repo_name)
        
    Raises:
        ValueError: If URL format is invalid
    """
    # Handle SSH format: git@github.com:owner/repo.git
    if repo_url.startswith('git@github.com:'):
        path = repo_url.replace('git@github.com:', '').rstrip('.git')
        parts = path.split('/')
        if len(parts) == 2:
            return parts[0], parts[1]
    
    # Handle HTTPS/HTTP formats
    # Add https:// if missing protocol
    if not repo_url.startswith(('http://', 'https://')):
        if repo_url.startswith('github.com'):
            repo_url = 'https://' + repo_url
        else:
            repo_url = 'https://github.com/' + repo_url
    
    # Parse the URL
    parsed = urlparse(repo_url)
    
    # Check if it's a GitHub URL
    if parsed.netloc != 'github.com':
        raise ValueError(f'Not a GitHub URL: {repo_url}')
    
    # Extract path components
    path = parsed.path.strip('/')
    if path.endswith('.git'):
        path = path[:-4]  # Remove exactly '.git' from the end
    parts = path.split('/')
    
    # Should have exactly 2 parts: owner/repo
    if len(parts) != 2 or not all(parts):
        raise ValueError(
            f'Invalid GitHub repository URL: {repo_url}. '
            'Expected format: https://github.com/owner/repo'
        )
    
    return parts[0], parts[1]


@router.post('/analyze-pr')
async def analyze_pr(request: AnalyzePRRequest) -> Dict[str, Any]:
    """
    Start asynchronous analysis of a Pull Request.
    Returns a task ID for tracking the analysis progress.
    """
    try:
        # Parse GitHub repository URL
        try:
            repo_owner, repo_name = parse_github_repo_url(request.repo_url)
            print(f"🔍 DEBUG: Parsed URL '{request.repo_url}' → Owner: '{repo_owner}', Repo: '{repo_name}'")
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        
        # Start the async task
        task = analyze_pr_task.delay(
            repo_owner,
            repo_name,
            request.pr_number,
            request.github_token
        )
        
        return {
            'task_id': task.id,
            'message': 'PR analysis started',
            'status': 'pending'
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, 
            detail=f'Failed to start PR analysis: {str(e)}'
        )


@router.get('/status/{task_id}')
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Check the status of a PR analysis task.
    
    Args:
        task_id: The ID of the analysis task
        
    Returns:
        Task status information
    """
    try:
        # Get task result with error handling
        task_result = AsyncResult(task_id, app=celery_app)
        
        # Safely get task state with error handling
        try:
            task_state = task_result.state
            task_info = task_result.info
        except ValueError as ve:
            # Handle Celery serialization errors
            print(f"Celery serialization error for task {task_id}: {ve}")
            return {
                'task_id': task_id,
                'status': 'error',
                'message': 'Task data corrupted. Please resubmit the request.',
                'error': 'Serialization error in task result'
            }
        except Exception as e:
            # Handle other Celery errors
            print(f"Celery error for task {task_id}: {e}")
            return {
                'task_id': task_id,
                'status': 'error',
                'message': 'Unable to retrieve task status',
                'error': str(e)
            }
        
        if task_state == 'PENDING':
            return {
                'task_id': task_id,
                'status': 'pending',
                'message': 'Task is waiting to be processed'
            }
        elif task_state == 'PROCESSING':
            message = 'Task is being processed'
            if task_info and isinstance(task_info, dict):
                message = task_info.get('message', message)
            return {
                'task_id': task_id,
                'status': 'processing',
                'message': message
            }
        elif task_state == 'SUCCESS':
            return {
                'task_id': task_id,
                'status': 'completed',
                'message': 'Analysis completed successfully'
            }
        elif task_state == 'FAILURE':
            error_message = 'Task failed'
            if task_info and isinstance(task_info, dict):
                error_message = task_info.get('message', error_message)
            elif isinstance(task_info, str):
                error_message = task_info
            
            return {
                'task_id': task_id,
                'status': 'failed',
                'message': error_message,
                'error': str(task_info) if task_info else 'Unknown error'
            }
        else:
            return {
                'task_id': task_id,
                'status': task_state.lower(),
                'message': f'Task state: {task_state}'
            }
            
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f'Failed to get task status: {str(e)}'
        )


@router.get('/results/{task_id}')
async def get_task_results(task_id: str) -> Dict[str, Any]:
    """
    Retrieve the results of a completed PR analysis task.
    
    Args:
        task_id: The ID of the analysis task
        
    Returns:
        Analysis results if the task is completed
    """
    try:
        # Get task result with error handling
        task_result = AsyncResult(task_id, app=celery_app)
        
        # Safely get task state
        try:
            task_state = task_result.state
            task_info = task_result.result
        except ValueError as ve:
            # Handle Celery serialization errors
            raise HTTPException(
                status_code=500,
                detail={
                    'task_id': task_id,
                    'status': 'error',
                    'message': 'Task data corrupted. Please resubmit the request.',
                    'error': 'Serialization error in task result'
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={
                    'task_id': task_id,
                    'status': 'error',
                    'message': 'Unable to retrieve task results',
                    'error': str(e)
                }
            )
        
        if task_state == 'PENDING':
            raise HTTPException(
                status_code=202,
                detail='Task is still pending. Check status first.'
            )
        elif task_state == 'PROCESSING':
            raise HTTPException(
                status_code=202,
                detail='Task is still processing. Check status first.'
            )
        elif task_state == 'SUCCESS':
            # Handle both dict and direct result formats
            if isinstance(task_info, dict):
                return {
                    'task_id': task_id,
                    'status': 'completed',
                    'results': task_info.get('results', task_info),
                    'message': task_info.get('message', 'Analysis completed')
                }
            else:
                return {
                    'task_id': task_id,
                    'status': 'completed',
                    'results': task_info,
                    'message': 'Analysis completed'
                }
        elif task_state == 'FAILURE':
            error_message = 'Task failed'
            if task_info and isinstance(task_info, dict):
                error_message = task_info.get('message', error_message)
            
            raise HTTPException(
                status_code=500,
                detail={
                    'task_id': task_id,
                    'status': 'failed',
                    'message': error_message,
                    'error': str(task_info) if task_info else 'Unknown error'
                }
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f'Task is in unexpected state: {task_state}'
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f'Failed to get task results: {str(e)}'
        )



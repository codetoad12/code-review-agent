"""
Celery tasks for asynchronous PR analysis.

This version integrates with the LangGraph-based code review agent
for sophisticated workflow orchestration.
"""
import traceback
from typing import Dict, Any
from celery import current_task
from celery_app import celery_app
from handlers.pr_handlers import GithubPrHandler
from agents.base_agent import BaseAgent


@celery_app.task(bind=True, name='tasks.analyze_pr_task')
def analyze_pr_task(self, repo_owner: str, repo_name: str, pr_number: int) -> Dict[str, Any]:
    """
    Async task to analyze a Pull Request.
    
    Args:
        repo_owner: GitHub repository owner
        repo_name: GitHub repository name  
        pr_number: Pull request number
        
    Returns:
        Analysis results or error information
    """
    try:
        # Update task status to processing
        self.update_state(
            state='PROCESSING',
            meta={'message': 'Fetching PR data from GitHub...'}
        )
        
        # Get PR data from GitHub
        try:
            github_pr_handler = GithubPrHandler(repo_owner, repo_name, pr_number)
            final_payload = github_pr_handler.format_pr_data_to_pass_to_agent()
        except Exception as e:
            error_msg = f'Failed to fetch PR data: {str(e)}'
            print(f'GitHub fetch error for task {self.request.id}: {error_msg}')
            
            self.update_state(
                state='FAILURE',
                meta={
                    'message': error_msg,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            )
            
            return {
                'task_id': self.request.id,
                'status': 'failed',
                'message': error_msg,
                'error': str(e)
            }
        
        # Update task status
        self.update_state(
            state='PROCESSING',
            meta={'message': 'Analyzing code with AI agents...'}
        )
        
        # Initialize the BaseAgent with the PR data (now using LangGraph)
        try:
            agent = BaseAgent(final_payload=final_payload)
            
            # Perform the analysis using LangGraph workflow
            analysis_result = agent.review()
            
            # Ensure the result is JSON serializable
            if analysis_result is None:
                analysis_result = {
                    'files': [],
                    'summary': {
                        'total_files': 0,
                        'total_issues': 0,
                        'critical_issues': 0
                    },
                    'message': 'No issues found'
                }
            
        except Exception as e:
            error_msg = f'Failed during code analysis: {str(e)}'
            print(f'Analysis error for task {self.request.id}: {error_msg}')
            print(f'Full traceback: {traceback.format_exc()}')
            
            self.update_state(
                state='FAILURE',
                meta={
                    'message': error_msg,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            )
            
            return {
                'task_id': self.request.id,
                'status': 'failed',
                'message': error_msg,
                'error': str(e)
            }
        
        # Return successful result - ensure it's JSON serializable
        result = {
            'task_id': self.request.id,
            'status': 'completed',
            'results': analysis_result,
            'message': 'PR analysis completed successfully'
        }
        
        # Validate the result is serializable
        try:
            import json
            json.dumps(result)  # Test serialization
        except (TypeError, ValueError) as e:
            error_msg = f'Result serialization failed: {str(e)}'
            print(f'Serialization error for task {self.request.id}: {error_msg}')
            
            # Return a safe, serializable error response
            return {
                'task_id': self.request.id,
                'status': 'failed',
                'message': 'Analysis completed but results could not be serialized',
                'error': str(e)
            }
        
        return result
        
    except Exception as e:
        # Catch-all error handler with safe serialization
        error_msg = f'Unexpected error in task: {str(e)}'
        error_traceback = traceback.format_exc()
        
        print(f'Unexpected error in task {self.request.id}: {error_msg}')
        print(f'Full traceback: {error_traceback}')
        
        # Update task state with safe, serializable data
        try:
            self.update_state(
                state='FAILURE',
                meta={
                    'message': error_msg,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            )
        except Exception as update_error:
            print(f'Failed to update task state: {update_error}')
        
        # Return safe, serializable error response
        return {
            'task_id': self.request.id,
            'status': 'failed',
            'message': error_msg,
            'error': str(e)
        }

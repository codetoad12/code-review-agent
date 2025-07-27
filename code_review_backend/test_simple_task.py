"""
Simple test task to isolate Celery serialization issues.
"""
import sys
import os
from celery_app import celery_app

@celery_app.task(bind=True, name='test_simple_task')
def simple_test_task(self, test_message: str):
    """
    A simple task that just returns a message - no complex logic.
    """
    try:
        print(f"🔄 Simple task started: {test_message}")
        
        # Update status
        self.update_state(
            state='PROCESSING',
            meta={'message': f'Processing: {test_message}'}
        )
        
        print(f"🔄 Processing task: {test_message}")
        
        # Simple operation
        result = {
            'task_id': self.request.id,
            'status': 'completed',
            'message': f'Simple task completed: {test_message}',
            'test_data': {
                'input': test_message,
                'length': len(test_message),
                'reversed': test_message[::-1]
            }
        }
        
        print(f"✅ Simple task completed successfully: {result}")
        return result
        
    except Exception as e:
        error_msg = f'Simple task failed: {str(e)}'
        print(f"❌ {error_msg}")
        
        # Import here to avoid circular imports
        import traceback
        traceback.print_exc()
        
        return {
            'task_id': self.request.id,
            'status': 'failed',
            'message': error_msg,
            'error': str(e)
        } 
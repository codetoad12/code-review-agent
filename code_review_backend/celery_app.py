"""
Celery configuration for async task processing.
"""
import os
import sys
from celery import Celery

# Create Celery app
celery_app = Celery('code_review_agent')

# Windows-specific configuration to avoid permission errors
worker_pool = 'threads' if sys.platform == 'win32' else 'prefork'

# Configure Celery
celery_app.conf.update(
    broker_url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    result_backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    result_expires=3600,  # Results expire after 1 hour
    # Windows compatibility settings
    worker_pool=worker_pool,
    worker_concurrency=2 if sys.platform == 'win32' else 4,
    # Auto-discover tasks - include both main tasks and test tasks
    include=['tasks', 'test_simple_task']
) 
#!/usr/bin/env python3
"""
Test script to verify Celery task registration and execution.
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from celery_app import celery_app
from tasks import analyze_pr_task

def test_task_registration():
    """Test if tasks are properly registered with Celery."""
    print("Testing Celery task registration...")
    
    # Check if tasks are registered
    registered_tasks = list(celery_app.tasks.keys())
    print(f"Registered tasks: {registered_tasks}")
    
    # Check if our specific task is registered
    task_name = 'tasks.analyze_pr_task'
    if task_name in registered_tasks:
        print(f"✅ Task '{task_name}' is properly registered!")
        return True
    else:
        print(f"❌ Task '{task_name}' is NOT registered!")
        print("Available tasks:")
        for task in registered_tasks:
            if not task.startswith('celery.'):
                print(f"  - {task}")
        return False

def test_redis_connection():
    """Test Redis connection."""
    print("\nTesting Redis connection...")
    try:
        # Try to get a connection to Redis
        from celery_app import celery_app
        inspector = celery_app.control.inspect()
        
        # This will raise an exception if Redis is not available
        stats = inspector.stats()
        if stats:
            print("✅ Redis connection successful!")
            print("✅ Celery workers found!")
        else:
            print("⚠️  Redis connection works, but no workers are running!")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

if __name__ == '__main__':
    print("=== Celery Configuration Test ===\n")
    
    task_ok = test_task_registration()
    redis_ok = test_redis_connection()
    
    print(f"\n=== Summary ===")
    print(f"Task Registration: {'✅ OK' if task_ok else '❌ FAILED'}")
    print(f"Redis Connection: {'✅ OK' if redis_ok else '❌ FAILED'}")
    
    if task_ok and redis_ok:
        print("\n🎉 Celery setup appears to be working!")
        print("Now start a worker with: celery -A celery_app worker --loglevel=info")
    else:
        print("\n🔧 Please fix the issues above before starting the worker.") 
#!/usr/bin/env python3
"""
Celery worker script to run async tasks.

Usage:
    python worker.py

Or with specific concurrency:
    celery -A celery_app worker --loglevel=info --concurrency=4
"""
import os
import sys

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from celery_app import celery_app

if __name__ == '__main__':
    # Start the worker
    celery_app.start(['worker', '--loglevel=info']) 
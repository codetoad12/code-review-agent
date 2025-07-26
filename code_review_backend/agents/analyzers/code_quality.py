"""
Code Quality Analyzer - Main Dispatcher

Handles routing to appropriate language-specific linters and provides
LLM fallback for unsupported languages.
"""

import os
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

from .linters.python_linter import PythonLinter
from .linters.js_linter import JSLinter
from .linters.go_linter import GoLinter
from .linters.rust_linter import RustLinter


class CodeQualityAnalyzer:
    """
    Main dispatcher for code quality analysis.
    Routes files to appropriate linters based on language detection.
    """
    
    def __init__(self):
        self.python_linter = PythonLinter()
        self.js_linter = JSLinter()
        self.go_linter = GoLinter()
        self.rust_linter = RustLinter()
        self.language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.jsx': 'JavaScript',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript',
            '.go': 'Go',
            '.rs': 'Rust',
        }
        
        # Common migration file patterns to exclude from linting
        self.migration_patterns = [
            # Django migrations
            r'.*/migrations/.*\.py$',
            r'.*/migrations/.*/.*\.py$',
            
            # Rails migrations
            r'db/migrate/.*\.rb$',
            
            # Laravel migrations
            r'database/migrations/.*\.php$',
            
            # Node.js migrations (Sequelize, Prisma, etc.)
            r'.*/migrations/.*\.js$',
            r'.*/migrations/.*\.ts$',
            
            # Alembic (SQLAlchemy) migrations
            r'.*/versions/.*\.py$',
            r'alembic/versions/.*\.py$',
            
            # Generic timestamp-based migration files
            r'.*\d{8,14}_.*\.(py|js|ts|rb|php)$',
            r'.*_\d{8,14}\.(py|js|ts|rb|php)$',
            
            # Other common patterns
            r'.*/schema\.rb$',  # Rails schema
            r'.*/seed.*\.(py|js|ts|rb|php)$',  # Seed files
        ]
    
    def analyze(self, filename: str, patch: str, raw_code: str, 
                changed_lines: List[int]) -> List[Dict[str, Any]]:
        """
        Analyze code quality for a given file.
        
        Args:
            filename: Name of the file being analyzed
            patch: Git diff patch content
            raw_code: Full content of the file
            changed_lines: List of line numbers that were changed
            
        Returns:
            List of issues in the standard format:
            [
                {
                    "type": "style|bug|performance|best_practice",
                    "line": int,
                    "description": str,
                    "suggestion": str
                }
            ]
        """
        # Skip linting for migration files
        if self._is_migration_file(filename):
            return []
        
        language = self._detect_language(filename)
        
        if language == 'Python':
            return self.python_linter.lint(filename, raw_code, changed_lines)
        elif language in ['JavaScript', 'TypeScript']:
            return self.js_linter.lint(filename, raw_code, changed_lines)
        elif language == 'Go':
            return self.go_linter.lint(filename, raw_code, changed_lines)
        elif language == 'Rust':
            return self.rust_linter.lint(filename, raw_code, changed_lines)
        else:
            return self._analyze_with_llm(filename, patch)
    
    def _is_migration_file(self, filename: str) -> bool:
        """
        Check if the file is a migration file that should be excluded from linting.
        
        Args:
            filename: Name of the file to check
            
        Returns:
            True if the file is a migration file, False otherwise
        """
        # Normalize path separators for cross-platform compatibility
        normalized_filename = filename.replace('\\', '/')
        
        for pattern in self.migration_patterns:
            if re.match(pattern, normalized_filename, re.IGNORECASE):
                return True
        
        return False
    
    def _detect_language(self, filename: str) -> Optional[str]:
        """Detect programming language from file extension."""
        ext = Path(filename).suffix.lower()
        return self.language_map.get(ext)
    
    def _analyze_with_llm(self, filename: str, patch: str) -> List[Dict[str, Any]]:
        """
        Fallback analysis using LLM for unsupported languages.
        
        Args:
            filename: Name of the file
            patch: Git diff patch content
            
        Returns:
            List of issues in standard format
        """
        # TODO: Implement LLM analysis using langchain/langgraph + Gemini
        # For now, return empty list
        return [] 
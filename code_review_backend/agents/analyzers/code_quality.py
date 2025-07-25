"""
Code Quality Analyzer - Main Dispatcher

Handles routing to appropriate language-specific linters and provides
LLM fallback for unsupported languages.
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from .linters.python_linter import PythonLinter


class CodeQualityAnalyzer:
    """
    Main dispatcher for code quality analysis.
    Routes files to appropriate linters based on language detection.
    """
    
    def __init__(self):
        self.python_linter = PythonLinter()
        self.language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.jsx': 'JavaScript',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript',
            '.go': 'Go',
            '.rs': 'Rust',
        }
    
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
        language = self._detect_language(filename)
        
        if language == 'Python':
            return self.python_linter.lint(filename, raw_code, changed_lines)
        elif language == 'Go':
            # TODO: Implement Go linter
            return self._analyze_with_llm(filename, patch)
        elif language == 'Rust':
            # TODO: Implement Rust linter
            return self._analyze_with_llm(filename, patch)
        elif language in ['JavaScript', 'TypeScript']:
            # TODO: Implement JS/TS linter
            return self._analyze_with_llm(filename, patch)
        else:
            return self._analyze_with_llm(filename, patch)
    
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
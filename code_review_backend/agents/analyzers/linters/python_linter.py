"""
Python Linter using Ruff

Provides comprehensive Python code analysis using the ruff linting tool.
Falls back to basic analysis if ruff is not available.
"""

import json
import subprocess
import tempfile
import os
from typing import List, Dict, Any, Optional
from pathlib import Path


class PythonLinter:
    """Python code linter using ruff tool."""
    
    def __init__(self):
        self.ruff_available = self._check_ruff_installation()
        
        # Mapping from ruff rule codes to issue types
        self.rule_type_mapping = {
            # Style issues (pycodestyle, formatting)
            'E': 'style',    # pycodestyle errors
            'W': 'style',    # pycodestyle warnings
            'I': 'style',    # isort import sorting
            'N': 'style',    # pep8-naming
            'D': 'style',    # pydocstyle
            'Q': 'style',    # flake8-quotes
            
            # Bug-related issues
            'F': 'bug',      # pyflakes (undefined names, imports)
            'B': 'bug',      # flake8-bugbear
            'A': 'bug',      # flake8-builtins
            'T': 'bug',      # flake8-print (debugging code left in)
            
            # Performance issues
            'C90': 'performance',  # mccabe complexity
            'UP': 'performance',   # pyupgrade
            'PERF': 'performance', # perflint
            
            # Best practices
            'S': 'best_practice',  # flake8-bandit (security)
            'C4': 'best_practice', # flake8-comprehensions
            'SIM': 'best_practice', # flake8-simplify
            'RET': 'best_practice', # flake8-return
            'ARG': 'best_practice', # flake8-unused-arguments
        }
    
    def lint(self, filename: str, raw_code: str, 
             changed_lines: List[int]) -> List[Dict[str, Any]]:
        """
        Lint Python code using ruff.
        
        Args:
            filename: Name of the file being analyzed
            raw_code: Full content of the file
            changed_lines: List of line numbers that were changed
            
        Returns:
            List of issues in standard format
        """
        if not self.ruff_available:
            return self._fallback_analysis(filename, raw_code, changed_lines)
        
        issues = []
        
        # Run ruff check for linting issues
        lint_issues = self._run_ruff_check(filename, raw_code, changed_lines)
        issues.extend(lint_issues)
        
        # Run ruff format check for formatting issues
        format_issues = self._run_ruff_format(filename, raw_code, changed_lines)
        issues.extend(format_issues)
        
        return issues
    
    def _check_ruff_installation(self) -> bool:
        """Check if ruff is installed and available."""
        try:
            result = subprocess.run(['ruff', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _run_ruff_check(self, filename: str, raw_code: str, 
                       changed_lines: List[int]) -> List[Dict[str, Any]]:
        """Run ruff check command and parse results."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(raw_code)
                temp_file.flush()
                
                # Run ruff check with JSON output
                result = subprocess.run([
                    'ruff', 'check', 
                    temp_file.name,
                    '--output-format', 'json',
                    '--no-fix'
                ], capture_output=True, text=True, timeout=30)
                
                os.unlink(temp_file.name)
                
                if result.returncode in [0, 1]:  # 0 = no issues, 1 = issues found
                    return self._parse_ruff_check_output(result.stdout, changed_lines)
                else:
                    print(f'Ruff check failed: {result.stderr}')
                    return []
                    
        except Exception as e:
            print(f'Error running ruff check: {e}')
            return []
    
    def _run_ruff_format(self, filename: str, raw_code: str, 
                        changed_lines: List[int]) -> List[Dict[str, Any]]:
        """Run ruff format check and identify formatting issues."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(raw_code)
                temp_file.flush()
                
                # Check if file needs formatting
                result = subprocess.run([
                    'ruff', 'format',
                    '--check',
                    temp_file.name
                ], capture_output=True, text=True, timeout=30)
                
                os.unlink(temp_file.name)
                
                if result.returncode == 1:  # File needs formatting
                    # For simplicity, report a general formatting issue
                    # In practice, we could diff the formatted vs original
                    return [{
                        'type': 'style',
                        'line': min(changed_lines) if changed_lines else 1,
                        'description': 'File formatting does not comply with standards',
                        'suggestion': 'Run `ruff format` to fix formatting issues'
                    }]
                
                return []
                
        except Exception as e:
            print(f'Error running ruff format: {e}')
            return []
    
    def _parse_ruff_check_output(self, output: str, 
                                changed_lines: List[int]) -> List[Dict[str, Any]]:
        """Parse ruff JSON output and convert to standard format."""
        if not output.strip():
            return []
        
        try:
            ruff_issues = json.loads(output)
        except json.JSONDecodeError:
            return []
        
        issues = []
        for issue in ruff_issues:
            line_number = issue.get('location', {}).get('row', 0)
            
            # Only include issues on changed lines
            if changed_lines and line_number not in changed_lines:
                continue
            
            rule_code = issue.get('code', '')
            issue_type = self._map_rule_to_type(rule_code)
            
            issues.append({
                'type': issue_type,
                'line': line_number,
                'description': issue.get('message', 'Unknown issue'),
                'suggestion': self._generate_suggestion(rule_code, issue.get('message', ''))
            })
        
        return issues
    
    def _map_rule_to_type(self, rule_code: str) -> str:
        """Map ruff rule code to issue type."""
        if not rule_code:
            return 'style'
        
        # Extract prefix (e.g., 'F' from 'F401')
        prefix = ''.join([c for c in rule_code if c.isalpha()])
        
        return self.rule_type_mapping.get(prefix, 'style')
    
    def _generate_suggestion(self, rule_code: str, message: str) -> str:
        """Generate helpful suggestion based on rule code and message."""
        suggestions = {
            'F401': 'Remove the unused import or use it in your code',
            'F841': 'Remove the unused variable or prefix with underscore if intentional',
            'E501': 'Break the line into multiple lines or use parentheses',
            'W292': 'Add a newline at the end of the file',
            'E302': 'Add two blank lines before function/class definitions',
            'E305': 'Add two blank lines after end of function or class',
        }
        
        return suggestions.get(rule_code, f'Fix: {message}')
    
    def _fallback_analysis(self, filename: str, raw_code: str, 
                          changed_lines: List[int]) -> List[Dict[str, Any]]:
        """
        Fallback analysis when ruff is not available.
        Performs basic Python syntax and style checks.
        """
        issues = []
        
        lines = raw_code.split('\n')
        for i, line in enumerate(lines, 1):
            if changed_lines and i not in changed_lines:
                continue
            
            # Basic checks
            if len(line) > 79:
                issues.append({
                    'type': 'style',
                    'line': i,
                    'description': f'Line too long ({len(line)} > 79 characters)',
                    'suggestion': 'Break line into multiple lines'
                })
            
            # Check for common issues
            stripped = line.strip()
            if stripped.endswith(';;'):
                issues.append({
                    'type': 'style',
                    'line': i,
                    'description': 'Double semicolon found',
                    'suggestion': 'Remove extra semicolon'
                })
        
        return issues 
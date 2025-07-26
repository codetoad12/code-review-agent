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
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(raw_code)
                temp_file.flush()
                temp_file_path = temp_file.name
            
            # Run ruff check with JSON output
            result = subprocess.run([
                'ruff', 'check', 
                temp_file_path,
                '--output-format', 'json',
                '--no-fix'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode in [0, 1]:  # 0 = no issues, 1 = issues found
                return self._parse_ruff_check_output(result.stdout, changed_lines)
            else:
                print(f'Ruff check failed: {result.stderr}')
                return []
                
        except Exception as e:
            print(f'Error running ruff check: {e}')
            return []
        finally:
            # Clean up temp file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except OSError as e:
                    print(f'Warning: Could not delete temp file {temp_file_path}: {e}')
    
    def _run_ruff_format(self, filename: str, raw_code: str, 
                        changed_lines: List[int]) -> List[Dict[str, Any]]:
        """Run ruff format check and identify specific formatting issues."""
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(raw_code)
                temp_file.flush()
                temp_file_path = temp_file.name
            
            # Check if file needs formatting
            result = subprocess.run([
                'ruff', 'format',
                '--check',
                '--diff',  # Show what would change
                temp_file_path
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 1:  # File needs formatting
                # Try to get more specific information from the diff
                diff_output = result.stdout.strip()
                
                if diff_output:
                    # Parse the diff to identify specific issues
                    formatting_issues = self._parse_format_diff(diff_output, changed_lines)
                    if formatting_issues:
                        return formatting_issues
                
                # Fallback to generic message if we can't parse specifics
                return [{
                    'type': 'style',
                    'line': min(changed_lines) if changed_lines else 1,
                    'description': 'Code formatting can be improved',
                    'suggestion': 'Run `ruff format` to automatically fix formatting issues'
                }]
            
            return []
                
        except Exception as e:
            print(f'Error running ruff format: {e}')
            return []
        finally:
            # Clean up temp file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except OSError as e:
                    print(f'Warning: Could not delete temp file {temp_file_path}: {e}')
    
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

    def _parse_format_diff(self, diff_output: str, changed_lines: List[int]) -> List[Dict[str, Any]]:
        """
        Parse ruff format diff output to identify specific formatting issues.
        
        Args:
            diff_output: The diff output from ruff format --diff
            changed_lines: Lines that were changed in the PR
            
        Returns:
            List of specific formatting issues
        """
        issues = []
        lines = diff_output.split('\n')
        
        current_line = 0
        for line in lines:
            # Look for line number indicators in diff
            if line.startswith('@@'):
                # Extract line number from hunk header like @@ -1,4 +1,4 @@
                import re
                match = re.search(r'\+(\d+)', line)
                if match:
                    current_line = int(match.group(1))
                continue
                    
            # Check for specific formatting changes
            if line.startswith('-') and not line.startswith('---'):
                # This is the original (incorrectly formatted) line
                original = line[1:]  # Remove the '-' prefix
                current_line += 1
                
                # Only report issues on changed lines
                if changed_lines and current_line not in changed_lines:
                    continue
                
                # Try to identify the type of formatting issue
                issue_desc = self._identify_formatting_issue(original, diff_output)
                
                issues.append({
                    'type': 'style',
                    'line': current_line,
                    'description': issue_desc,
                    'suggestion': 'Run `ruff format` to fix formatting'
                })
                
            elif line.startswith('+') and not line.startswith('+++'):
                # Skip the correctly formatted version
                continue
                
        return issues
    
    def _identify_formatting_issue(self, original_line: str, context: str) -> str:
        """
        Try to identify the specific type of formatting issue.
        
        Args:
            original_line: The original (incorrectly formatted) line
            context: Full diff context for additional clues
            
        Returns:
            Description of the formatting issue
        """
        # Check for common formatting issues
        
        if original_line.rstrip() != original_line:
            return 'Trailing whitespace detected'
            
        if '\t' in original_line:
            return 'Tab characters should be replaced with spaces'
            
        if original_line.startswith(' ' * 8) and '    ' not in original_line:
            return 'Inconsistent indentation (should use 4 spaces)'
            
        if '"' in original_line and "'" in original_line:
            return 'Inconsistent quote usage'
            
        if len(original_line) > 88:  # Ruff default line length
            return f'Line too long ({len(original_line)} characters)'
            
        # Generic fallback
        return 'Code formatting can be improved' 
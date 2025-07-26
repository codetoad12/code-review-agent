"""
JavaScript/TypeScript Linter using ESLint

Provides comprehensive JavaScript and TypeScript code analysis using ESLint.
Falls back to basic analysis if ESLint is not available.
"""

import json
import subprocess
import tempfile
import os
from typing import List, Dict, Any, Optional
from pathlib import Path


class JSLinter:
    """JavaScript/TypeScript code linter using ESLint tool."""
    
    def __init__(self):
        self.eslint_command = None
        self.eslint_available = self._check_eslint_installation()
        
        # Basic ESLint configuration for when no project config exists
        self.basic_config = {
            'env': {
                'browser': True,
                'node': True,
                'es2021': True
            },
            'extends': ['eslint:recommended'],
            'parserOptions': {
                'ecmaVersion': 2021,
                'sourceType': 'module'
            },
            'rules': {
                # Error-level rules (bugs)
                'no-unused-vars': 'error',
                'no-undef': 'error',
                'no-redeclare': 'error',
                'no-unreachable': 'error',
                
                # Warning-level rules (style/best practices)
                'quotes': ['warn', 'single'],
                'semi': ['warn', 'always'],
                'eqeqeq': ['warn', 'always'],
                'no-eval': 'warn',
                'no-console': 'warn',
                'prefer-const': 'warn',
            }
        }
        
        # TypeScript-specific configuration
        self.typescript_config = {
            'parser': '@typescript-eslint/parser',
            'plugins': ['@typescript-eslint'],
            'extends': [
                'eslint:recommended',
                '@typescript-eslint/recommended'
            ],
            'rules': {
                **self.basic_config['rules'],
                '@typescript-eslint/no-unused-vars': 'error',
                '@typescript-eslint/no-explicit-any': 'warn',
                '@typescript-eslint/prefer-nullish-coalescing': 'warn',
            }
        }
        
        # Mapping from ESLint severity to issue types
        self.severity_mapping = {
            1: 'style',      # ESLint warning
            2: 'bug',        # ESLint error
        }
        
        # Rule-specific type overrides
        self.rule_type_mapping = {
            # Performance-related rules
            'prefer-const': 'performance',
            'no-loop-func': 'performance',
            
            # Best practice rules
            'eqeqeq': 'best_practice',
            'no-eval': 'best_practice',
            'no-implied-eval': 'best_practice',
            'prefer-template': 'best_practice',
            'prefer-arrow-callback': 'best_practice',
        }
    
    def lint(self, filename: str, raw_code: str, 
             changed_lines: List[int]) -> List[Dict[str, Any]]:
        """
        Lint JavaScript/TypeScript code using ESLint.
        
        Args:
            filename: Name of the file being analyzed
            raw_code: Full content of the file
            changed_lines: List of line numbers that were changed
            
        Returns:
            List of issues in standard format
        """
        if not self.eslint_available:
            return self._fallback_analysis(filename, raw_code, changed_lines)
        
        return self._run_eslint(filename, raw_code, changed_lines)
    
    def _check_eslint_installation(self) -> bool:
        """Check ESLint installation and determine the best command to use."""
        # Try different ESLint installation methods
        eslint_commands = [
            ['npx', 'eslint'],           # npx (most reliable)
            ['./node_modules/.bin/eslint'], # Local installation
            ['eslint'],                  # Global installation
        ]
        
        for cmd in eslint_commands:
            try:
                result = subprocess.run(
                    cmd + ['--version'], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                if result.returncode == 0:
                    self.eslint_command = cmd
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue
        
        return False
    
    def _run_eslint(self, filename: str, raw_code: str, 
                   changed_lines: List[int]) -> List[Dict[str, Any]]:
        """Run ESLint and parse results."""
        temp_file_path = None
        config_file_path = None
        
        try:
            # Determine file type and appropriate config
            is_typescript = self._is_typescript_file(filename)
            config = (self.typescript_config if is_typescript 
                     else self.basic_config)
            
            # Create temporary source file
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix=self._get_file_extension(filename), 
                delete=False
            ) as temp_file:
                temp_file.write(raw_code)
                temp_file.flush()
                temp_file_path = temp_file.name
            
            # Create temporary config file
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.json', 
                delete=False
            ) as config_file:
                json.dump(config, config_file)
                config_file.flush()
                config_file_path = config_file.name
            
            # Run ESLint with JSON output
            result = subprocess.run(
                self.eslint_command + [
                    temp_file_path,
                    '--format', 'json',
                    '--config', config_file_path,
                    '--no-eslintrc'  # Ignore project config
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return self._parse_eslint_output(
                result.stdout, changed_lines
            )
                    
        except Exception as e:
            print(f'Error running ESLint: {e}')
            return self._fallback_analysis(filename, raw_code, changed_lines)
        finally:
            # Clean up temp files
            for file_path in [temp_file_path, config_file_path]:
                if file_path and os.path.exists(file_path):
                    try:
                        os.unlink(file_path)
                    except OSError as e:
                        print(f'Warning: Could not delete temp file {file_path}: {e}')
    
    def _parse_eslint_output(self, output: str, 
                            changed_lines: List[int]) -> List[Dict[str, Any]]:
        """Parse ESLint JSON output and convert to standard format."""
        if not output.strip():
            return []
        
        try:
            eslint_results = json.loads(output)
        except json.JSONDecodeError:
            return []
        
        issues = []
        
        # ESLint returns array of file results
        for file_result in eslint_results:
            messages = file_result.get('messages', [])
            
            for message in messages:
                line_number = message.get('line', 0)
                
                # Only include issues on changed lines
                if changed_lines and line_number not in changed_lines:
                    continue
                
                rule_id = message.get('ruleId', '')
                severity = message.get('severity', 1)
                
                # Determine issue type
                issue_type = self._determine_issue_type(rule_id, severity)
                
                issues.append({
                    'type': issue_type,
                    'line': line_number,
                    'description': message.get('message', 'Unknown issue'),
                    'suggestion': self._generate_suggestion(
                        rule_id, message.get('message', '')
                    )
                })
        
        return issues
    
    def _determine_issue_type(self, rule_id: str, severity: int) -> str:
        """Determine issue type based on rule ID and severity."""
        # Check rule-specific overrides first
        if rule_id in self.rule_type_mapping:
            return self.rule_type_mapping[rule_id]
        
        # Fall back to severity mapping
        return self.severity_mapping.get(severity, 'style')
    
    def _generate_suggestion(self, rule_id: str, message: str) -> str:
        """Generate helpful suggestion based on ESLint rule."""
        suggestions = {
            'no-unused-vars': 'Remove the unused variable or prefix with underscore',
            'no-undef': 'Define the variable or import it from appropriate module',
            'quotes': 'Use consistent quote style throughout the file',
            'semi': 'Add or remove semicolons consistently',
            'eqeqeq': 'Use strict equality (===) instead of loose equality (==)',
            'no-eval': 'Avoid using eval() as it poses security risks',
            'no-console': 'Remove console.log statements before production',
            'prefer-const': 'Use const for variables that are never reassigned',
            'no-redeclare': 'Avoid redeclaring the same variable',
            'no-unreachable': 'Remove unreachable code after return/throw',
        }
        
        return suggestions.get(rule_id, f'Fix: {message}')
    
    def _is_typescript_file(self, filename: str) -> bool:
        """Check if file is TypeScript."""
        ext = Path(filename).suffix.lower()
        return ext in ['.ts', '.tsx']
    
    def _get_file_extension(self, filename: str) -> str:
        """Get appropriate file extension for temp file."""
        ext = Path(filename).suffix.lower()
        if ext in ['.js', '.jsx', '.ts', '.tsx']:
            return ext
        return '.js'  # Default fallback
    
    def _fallback_analysis(self, filename: str, raw_code: str, 
                          changed_lines: List[int]) -> List[Dict[str, Any]]:
        """
        Fallback analysis when ESLint is not available.
        Performs basic JavaScript/TypeScript syntax and style checks.
        """
        issues = []
        lines = raw_code.split('\n')
        
        for i, line in enumerate(lines, 1):
            if changed_lines and i not in changed_lines:
                continue
            
            stripped = line.strip()
            
            # Basic style checks
            if len(line) > 120:  # More lenient than Python
                issues.append({
                    'type': 'style',
                    'line': i,
                    'description': f'Line too long ({len(line)} > 120 characters)',
                    'suggestion': 'Break line into multiple lines'
                })
            
            # Check for common issues
            if 'var ' in line and not line.strip().startswith('//'):
                issues.append({
                    'type': 'best_practice',
                    'line': i,
                    'description': 'Use "const" or "let" instead of "var"',
                    'suggestion': 'Replace "var" with "const" or "let"'
                })
            
            if '==' in stripped and '===' not in stripped:
                issues.append({
                    'type': 'best_practice',
                    'line': i,
                    'description': 'Use strict equality (===) instead of loose equality (==)',
                    'suggestion': 'Replace == with ==='
                })
            
            if 'console.log(' in stripped:
                issues.append({
                    'type': 'style',
                    'line': i,
                    'description': 'Console statement found',
                    'suggestion': 'Remove console.log before production'
                })
        
        return issues 
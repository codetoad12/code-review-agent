"""
Go Linter using golangci-lint with comprehensive fallback

Provides Go code analysis using golangci-lint when available.
Falls back to comprehensive pattern-based analysis when Go is not installed.
"""

import json
import subprocess
import tempfile
import os
import re
from typing import List, Dict, Any, Optional
from pathlib import Path


class GoLinter:
    """Go code linter using golangci-lint tool with robust fallback."""
    
    def __init__(self):
        self.golangci_command = None
        self.golangci_available = self._check_golangci_installation()
        
        # Basic golangci-lint configuration
        self.basic_config = {
            'linters': {
                'enable': [
                    'gofmt',      # Formatting
                    'govet',      # Suspicious constructs  
                    'ineffassign', # Ineffectual assignments
                    'gosec',      # Security issues
                    'staticcheck', # Advanced static analysis
                    'unused',     # Unused code
                    'errcheck',   # Unchecked errors
                ]
            },
            'issues': {
                'exclude-use-default': False
            }
        }
        
        # Mapping from golangci-lint severity to issue types
        self.severity_mapping = {
            'error': 'bug',
            'warning': 'style',
            'info': 'style'
        }
        
        # Linter-specific type overrides
        self.linter_type_mapping = {
            # Performance-related linters
            'ineffassign': 'performance',
            'prealloc': 'performance',
            'maligned': 'performance',
            
            # Security linters
            'gosec': 'best_practice',
            'gas': 'best_practice',
            
            # Best practice linters
            'errcheck': 'best_practice',
            'unconvert': 'best_practice',
            'goconst': 'best_practice',
        }
    
    def lint(self, filename: str, raw_code: str, 
             changed_lines: List[int]) -> List[Dict[str, Any]]:
        """
        Lint Go code using golangci-lint or fallback analysis.
        
        Args:
            filename: Name of the file being analyzed
            raw_code: Full content of the file
            changed_lines: List of line numbers that were changed
            
        Returns:
            List of issues in standard format
        """
        if self.golangci_available:
            return self._run_golangci_lint(filename, raw_code, changed_lines)
        else:
            return self._fallback_analysis(filename, raw_code, changed_lines)
    
    def _check_golangci_installation(self) -> bool:
        """Check golangci-lint installation and determine the best command to use."""
        # Try different golangci-lint installation methods
        golangci_commands = [
            ['golangci-lint'],           # Direct installation
            ['go', 'run', 'github.com/golangci/golangci-lint/cmd/golangci-lint@latest'], # Go run
        ]
        
        for cmd in golangci_commands:
            try:
                result = subprocess.run(
                    cmd + ['--version'], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                if result.returncode == 0:
                    self.golangci_command = cmd
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue
        
        return False
    
    def _run_golangci_lint(self, filename: str, raw_code: str, 
                          changed_lines: List[int]) -> List[Dict[str, Any]]:
        """Run golangci-lint and parse results."""
        temp_file_path = None
        config_file_path = None
        
        try:
            # Create temporary Go file
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.go', 
                delete=False,
                encoding='utf-8'
            ) as temp_file:
                temp_file.write(raw_code)
                temp_file.flush()
                temp_file_path = temp_file.name
            
            # Create temporary config file
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.yaml', 
                delete=False,
                encoding='utf-8'
            ) as config_file:
                # Convert config to YAML format for golangci-lint
                config_yaml = self._dict_to_yaml(self.basic_config)
                config_file.write(config_yaml)
                config_file.flush()
                config_file_path = config_file.name
            
            # Run golangci-lint with JSON output
            result = subprocess.run(
                self.golangci_command + [
                    'run',
                    '--out-format', 'json',
                    '--config', config_file_path,
                    temp_file_path
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return self._parse_golangci_output(
                result.stdout, changed_lines
            )
                    
        except Exception as e:
            print(f'Error running golangci-lint: {e}')
            return self._fallback_analysis(filename, raw_code, changed_lines)
        finally:
            # Clean up temp files
            for file_path in [temp_file_path, config_file_path]:
                if file_path and os.path.exists(file_path):
                    try:
                        os.unlink(file_path)
                    except OSError as e:
                        print(f'Warning: Could not delete temp file {file_path}: {e}')
    
    def _parse_golangci_output(self, output: str, 
                              changed_lines: List[int]) -> List[Dict[str, Any]]:
        """Parse golangci-lint JSON output and convert to standard format."""
        if not output.strip():
            return []
        
        try:
            golangci_results = json.loads(output)
        except json.JSONDecodeError:
            return []
        
        issues = []
        
        # golangci-lint returns {Issues: [...]}
        for issue in golangci_results.get('Issues', []):
            line_number = issue.get('Pos', {}).get('Line', 0)
            
            # Only include issues on changed lines
            if changed_lines and line_number not in changed_lines:
                continue
            
            linter_name = issue.get('FromLinter', '')
            severity = issue.get('Severity', 'warning')
            
            # Determine issue type
            issue_type = self._determine_issue_type(linter_name, severity)
            
            issues.append({
                'type': issue_type,
                'line': line_number,
                'description': issue.get('Text', 'Unknown issue'),
                'suggestion': self._generate_suggestion(
                    linter_name, issue.get('Text', '')
                )
            })
        
        return issues
    
    def _determine_issue_type(self, linter_name: str, severity: str) -> str:
        """Determine issue type based on linter name and severity."""
        # Check linter-specific overrides first
        if linter_name in self.linter_type_mapping:
            return self.linter_type_mapping[linter_name]
        
        # Fall back to severity mapping
        return self.severity_mapping.get(severity, 'style')
    
    def _generate_suggestion(self, linter_name: str, message: str) -> str:
        """Generate helpful suggestion based on golangci-lint linter."""
        suggestions = {
            'gofmt': 'Run `gofmt -w` to fix formatting',
            'govet': 'Review the code for potential runtime issues',
            'ineffassign': 'Remove the ineffectual assignment',
            'gosec': 'Review for security implications',
            'errcheck': 'Add proper error handling',
            'unused': 'Remove unused code or mark with underscore if intentional',
            'staticcheck': 'Review static analysis suggestions',
        }
        
        return suggestions.get(linter_name, f'Fix: {message}')
    
    def _dict_to_yaml(self, config_dict: Dict) -> str:
        """Convert config dictionary to simple YAML format."""
        # Simple YAML conversion for basic config
        yaml_lines = []
        for key, value in config_dict.items():
            if isinstance(value, dict):
                yaml_lines.append(f'{key}:')
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, list):
                        yaml_lines.append(f'  {subkey}:')
                        for item in subvalue:
                            yaml_lines.append(f'    - {item}')
                    else:
                        yaml_lines.append(f'  {subkey}: {subvalue}')
            else:
                yaml_lines.append(f'{key}: {value}')
        return '\n'.join(yaml_lines)
    
    def _fallback_analysis(self, filename: str, raw_code: str, 
                          changed_lines: List[int]) -> List[Dict[str, Any]]:
        """
        Comprehensive fallback analysis when golangci-lint is not available.
        Performs pattern-based Go code analysis.
        """
        issues = []
        lines = raw_code.split('\n')
        
        # Track if we've seen a package declaration
        has_package = False
        
        for i, line in enumerate(lines, 1):
            if changed_lines and i not in changed_lines:
                continue
            
            stripped = line.strip()
            
            # Check for package declaration
            if stripped.startswith('package '):
                has_package = True
            
            # Basic style checks
            if len(line) > 100:  # Go convention
                issues.append({
                    'type': 'style',
                    'line': i,
                    'description': f'Line too long ({len(line)} > 100 characters)',
                    'suggestion': 'Break line into multiple lines'
                })
            
            # Check for debugging statements
            if re.search(r'\bfmt\.Print[fl]?\(', stripped):
                issues.append({
                    'type': 'style',
                    'line': i,
                    'description': 'Debug print statement found',
                    'suggestion': 'Remove fmt.Print* statements before production'
                })
            
            # Check for panic in inappropriate contexts
            if 'panic(' in stripped and not stripped.startswith('//'):
                issues.append({
                    'type': 'bug',
                    'line': i,
                    'description': 'panic() call found',
                    'suggestion': 'Consider proper error handling instead of panic'
                })
            
            # Check for unused variable pattern
            if re.match(r'^\s*\w+\s*:=.*', stripped) and '_' not in stripped:
                # This is a heuristic - not always accurate
                var_name = re.match(r'^\s*(\w+)\s*:=', stripped)
                if var_name:
                    var = var_name.group(1)
                    # Check if variable is used in subsequent lines (simple check)
                    remaining_code = '\n'.join(lines[i:i+5])  # Check next 5 lines
                    if var not in remaining_code:
                        issues.append({
                            'type': 'performance',
                            'line': i,
                            'description': f'Variable "{var}" may be unused',
                            'suggestion': f'Remove unused variable or use underscore: _ = {var}'
                        })
            
            # Check for error handling patterns
            if 'err :=' in stripped or 'err =' in stripped:
                # Look for proper error checking in next few lines
                next_lines = lines[i:i+3] if i < len(lines) - 2 else lines[i:]
                has_error_check = any('if err != nil' in l for l in next_lines)
                if not has_error_check:
                    issues.append({
                        'type': 'best_practice',
                        'line': i,
                        'description': 'Error not checked',
                        'suggestion': 'Add proper error handling: if err != nil { ... }'
                    })
            
            # Check for hardcoded secrets/passwords
            if re.search(r'(password|secret|key|token)\s*[:=]\s*["\']', stripped, re.I):
                issues.append({
                    'type': 'best_practice',
                    'line': i,
                    'description': 'Possible hardcoded secret detected',
                    'suggestion': 'Use environment variables or secure config for secrets'
                })
            
            # Check for SQL injection risks
            if re.search(r'(Query|Exec)\s*\([^?]*\+', stripped):
                issues.append({
                    'type': 'best_practice',
                    'line': i,
                    'description': 'Possible SQL injection risk',
                    'suggestion': 'Use parameterized queries with placeholders'
                })
        
        # Check for missing package declaration
        if not has_package and raw_code.strip():
            issues.append({
                'type': 'bug',
                'line': 1,
                'description': 'Missing package declaration',
                'suggestion': 'Add package declaration at the top of the file'
            })
        
        return issues 
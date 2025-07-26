"""
Python Bug Heuristics

Static analysis heuristics to detect common Python bug patterns.
Focuses on potential runtime errors and logic issues.
"""

import ast
import re
from typing import List, Dict, Any, Set, Optional


class PythonBugHeuristics:
    """
    Static heuristics for detecting potential bugs in Python code.
    
    This class implements rule-based detection for common Python bug 
    patterns that could lead to runtime errors or unexpected behavior.
    """
    
    def __init__(self):
        """Initialize the heuristics analyzer."""
        pass
    
    def analyze(self, filename: str, raw_code: str, 
                changed_lines: List[int]) -> List[Dict[str, Any]]:
        """
        Analyze Python code for potential bug patterns.
        
        Args:
            filename: Name of the file being analyzed
            raw_code: Full content of the Python file
            changed_lines: List of line numbers that were changed
            
        Returns:
            List of potential bug issues in standard format:
            [
                {
                    "type": "bug",
                    "line": int,
                    "description": str,
                    "suggestion": str
                }
            ]
        """
        issues = []
        lines = raw_code.split('\n')
        
        # Run all heuristic checks
        issues.extend(self._check_unsafe_dict_access(lines, changed_lines))
        issues.extend(self._check_file_operations_without_context(
            lines, changed_lines))
        issues.extend(self._check_potential_zero_division(
            lines, changed_lines))
        issues.extend(self._check_unsafe_attribute_access(
            lines, changed_lines))
        
        return issues
    
    def _check_unsafe_dict_access(self, lines: List[str], 
                                 changed_lines: List[int]) -> List[Dict[str, Any]]:
        """
        Detect dictionary key access without using .get() method.
        
        Pattern: dict[key] instead of dict.get(key) or 
                dict.get(key, default)
        """
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            if line_num not in changed_lines:
                continue
                
            line = line.strip()
            
            # Skip comments and docstrings
            if line.startswith('#') or line.startswith('"""') or line.startswith("'''"):
                continue
            
            # Look for dictionary access patterns
            # Pattern: variable[key] where variable might be a dict
            dict_access_pattern = r'(\w+)\[([^\]]+)\]'
            matches = re.finditer(dict_access_pattern, line)
            
            for match in matches:
                var_name = match.group(1)
                key_access = match.group(2)
                
                # Skip if it's clearly an array/list index (numeric)
                if key_access.strip().isdigit():
                    continue
                
                # Skip if it's a string literal being indexed
                if var_name in ['str', 'string'] or key_access.startswith('"') or key_access.startswith("'"):
                    continue
                
                # Check if this looks like dict access
                # Heuristic: if key is quoted string or variable, likely dict
                if (key_access.startswith('"') and key_access.endswith('"')) or \
                   (key_access.startswith("'") and key_access.endswith("'")) or \
                   (not key_access.isdigit() and ':' not in key_access):
                    
                    issues.append({
                        'type': 'bug',
                        'line': line_num,
                        'description': (
                            f'Unsafe dictionary access: {var_name}[{key_access}] '
                            f'may raise KeyError if key doesn\'t exist'
                        ),
                        'suggestion': (
                            f'Consider using {var_name}.get({key_access}) or '
                            f'{var_name}.get({key_access}, default_value) for '
                            f'safer access'
                        )
                    })
        
        return issues
    
    def _check_file_operations_without_context(
        self, lines: List[str], changed_lines: List[int]
    ) -> List[Dict[str, Any]]:
        """
        Detect file operations not using 'with' statement for proper 
        resource management.
        
        Pattern: open() calls not within 'with' context
        """
        issues = []
        in_with_block = False
        with_block_level = 0
        
        for line_num, line in enumerate(lines, 1):
            if line_num not in changed_lines:
                continue
                
            stripped_line = line.strip()
            
            # Skip comments
            if stripped_line.startswith('#'):
                continue
            
            # Track with statement blocks
            if 'with ' in stripped_line and 'open(' in stripped_line:
                in_with_block = True
                with_block_level = len(line) - len(line.lstrip())
                continue
            
            # Check if we're still in with block
            if in_with_block:
                current_indent = len(line) - len(line.lstrip())
                if stripped_line and current_indent <= with_block_level:
                    in_with_block = False
                    with_block_level = 0
            
            # Look for open() calls outside with blocks
            if 'open(' in stripped_line and not in_with_block:
                # Make sure it's not already in a with statement on same line
                if not re.search(r'with\s+.*open\s*\(', stripped_line):
                    # Check if it's an assignment (potential resource leak)
                    if '=' in stripped_line:
                        issues.append({
                            'type': 'bug',
                            'line': line_num,
                            'description': (
                                'File opened without context manager '
                                '(with statement) - potential resource leak'
                            ),
                            'suggestion': (
                                'Use "with open(...) as f:" to ensure '
                                'proper file closure'
                            )
                        })
        
        return issues
    
    def _check_potential_zero_division(
        self, lines: List[str], changed_lines: List[int]
    ) -> List[Dict[str, Any]]:
        """
        Detect division operations that might involve zero divisor.
        
        Patterns:
        - Direct division by variables
        - Division in loops where divisor might become zero
        - Modulo operations with potential zero
        """
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            if line_num not in changed_lines:
                continue
                
            stripped_line = line.strip()
            
            # Skip comments
            if stripped_line.startswith('#'):
                continue
            
            # Look for division patterns
            division_patterns = [
                r'(\w+)\s*/\s*(\w+)',  # variable / variable
                r'(\w+)\s*%\s*(\w+)',  # variable % variable (modulo)
            ]
            
            for pattern in division_patterns:
                matches = re.finditer(pattern, stripped_line)
                
                for match in matches:
                    numerator = match.group(1)
                    denominator = match.group(2)
                    
                    # Skip if denominator is clearly non-zero literal
                    if denominator.isdigit() and int(denominator) != 0:
                        continue
                    
                    # Skip if there's already a zero check visible
                    if f'if {denominator}' in stripped_line or \
                       f'{denominator} != 0' in stripped_line or \
                       f'{denominator} > 0' in stripped_line:
                        continue
                    
                    operation = '/' if '/' in match.group(0) else '%'
                    
                    issues.append({
                        'type': 'bug',
                        'line': line_num,
                        'description': (
                            f'Potential division by zero: {numerator} '
                            f'{operation} {denominator} could raise '
                            f'ZeroDivisionError'
                        ),
                        'suggestion': (
                            f'Add zero check: if {denominator} != 0: '
                            f'before division operation'
                        )
                    })
        
        return issues
    
    def _check_unsafe_attribute_access(
        self, lines: List[str], changed_lines: List[int]
    ) -> List[Dict[str, Any]]:
        """
        Detect attribute access that might fail with AttributeError.
        
        Patterns:
        - obj.attr without None check
        - Chained attribute access: obj.attr1.attr2
        """
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            if line_num not in changed_lines:
                continue
                
            stripped_line = line.strip()
            
            # Skip comments and imports
            if stripped_line.startswith('#') or \
               stripped_line.startswith('import ') or \
               stripped_line.startswith('from '):
                continue
            
            # Look for attribute access patterns
            # Pattern: obj.attr or obj.attr1.attr2.attr3
            attr_access_pattern = r'(\w+)(\.\w+)+'
            matches = re.finditer(attr_access_pattern, stripped_line)
            
            for match in matches:
                full_access = match.group(0)
                base_obj = match.group(1)
                
                # Skip common safe patterns
                if base_obj in ['self', 'cls', 'os', 'sys', 'json', 're']:
                    continue
                
                # Skip if there's already a None check
                if f'if {base_obj}' in stripped_line or \
                   f'{base_obj} is not None' in stripped_line or \
                   f'{base_obj} and ' in stripped_line:
                    continue
                
                # Count attribute levels
                attr_count = full_access.count('.')
                
                # Flag chained attribute access (more risky)
                if attr_count >= 2:
                    issues.append({
                        'type': 'bug',
                        'line': line_num,
                        'description': (
                            f'Chained attribute access "{full_access}" '
                            f'may raise AttributeError if any object '
                            f'in chain is None'
                        ),
                        'suggestion': (
                            f'Consider using getattr() or check if '
                            f'{base_obj} is not None before accessing '
                            f'attributes'
                        )
                    })
        
        return issues 
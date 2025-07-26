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
                
                # Skip if it's a string literal being indexed (not dict access)
                if var_name in ['str', 'string']:
                    continue
                
                # Check if this looks like dict access
                # Heuristic: if key is quoted string or variable, likely dict
                is_string_key = (key_access.startswith('"') and key_access.endswith('"')) or \
                               (key_access.startswith("'") and key_access.endswith("'"))
                is_variable_key = (not key_access.isdigit() and ':' not in key_access 
                                 and not (key_access.startswith('[') and key_access.endswith(']')))
                
                if is_string_key or is_variable_key:
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
        Detect potentially unsafe attribute access that might fail with 
        AttributeError.
        
        Focuses on risky patterns while avoiding false positives from 
        common framework patterns.
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
                
                # Skip built-in safe patterns
                if self._is_safe_attribute_pattern(base_obj, full_access, 
                                                  stripped_line):
                    continue
                
                # Skip if there's already a None check
                if (f'if {base_obj}' in stripped_line or 
                   f'{base_obj} is not None' in stripped_line or 
                   f'{base_obj} and ' in stripped_line):
                    continue
                
                # Only flag risky patterns (3+ levels of pure attribute access)
                attr_count = full_access.count('.')
                
                # Check if it's mostly method calls vs attribute access
                if attr_count >= 3 and self._is_risky_attribute_chain(full_access):
                    issues.append({
                        'type': 'bug',
                        'line': line_num,
                        'description': (
                            f'Deep chained attribute access "{full_access}" '
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
    
    def _is_safe_attribute_pattern(self, base_obj: str, full_access: str, 
                                  line: str) -> bool:
        """
        Check if this is a known safe attribute access pattern.
        """
        # Common safe base objects (modules, built-ins, framework objects)
        safe_base_objects = {
            'self', 'cls', 'super', 'os', 'sys', 'json', 're', 'datetime',
            'settings', 'config', 'request', 'response', 'app', 'db',
            'logger', 'log', 'math', 'random', 'time', 'uuid',
            # Common modules that appear in imports/references
            'django', 'flask', 'fastapi', 'requests', 'urllib', 'http',
            'typing', 'collections', 'functools', 'itertools', 'pathlib'
        }
        
        if base_obj in safe_base_objects:
            return True
        
        # Check if this looks like a module import or class reference
        if self._is_module_or_class_reference(full_access, line):
            return True
        
        # Django ORM patterns
        if '.objects.' in full_access:
            return True
        
        # Method chaining patterns (safer than pure attribute access)
        if '()' in line and full_access in line:
            # Check if most of the chain consists of method calls
            method_call_count = line.count('()')  
            attr_count = full_access.count('.')
            if method_call_count >= attr_count - 1:
                return True
        
        # Common framework patterns
        safe_patterns = [
            '.Meta.', '.DoesNotExist', '.MultipleObjectsReturned',
            '.cleaned_data.', '.is_valid', '.save', '.delete',
            '.filter', '.exclude', '.get', '.create', '.update',
            '.first', '.last', '.count', '.exists',
            '.user.', '.session.', '.GET.', '.POST.',
            '.status_code', '.content', '.headers',
            '.pk', '.id', '.name', '.models.', '.db.'
        ]
        
        for pattern in safe_patterns:
            if pattern in full_access:
                return True
        
        return False
    
    def _is_module_or_class_reference(self, full_access: str, line: str) -> bool:
        """
        Check if this looks like a static module path or class reference
        rather than runtime attribute access.
        """
        # Class references often end with capitalized names
        parts = full_access.split('.')
        last_part = parts[-1]
        
        # If the last part is capitalized, likely a class reference
        if last_part and last_part[0].isupper():
            return True
        
        # Check for import statements specifically
        stripped_line = line.strip()
        if (stripped_line.startswith('import ') or 
            stripped_line.startswith('from ') or
            'import ' + full_access in line or
            'from ' + full_access in line):
            return True
        
        # Type-related function calls
        if ('isinstance(' in line or 'issubclass(' in line or
            'typing.' in line):
            return True
        
        # Generic type hints in brackets
        type_hint_patterns = ['Type[', 'Optional[', 'Union[', 'List[', 
                             'Dict[', 'Tuple[', 'Set[']
        for pattern in type_hint_patterns:
            if pattern in line and full_access in line:
                return True
        
        # Django field definitions (very specific context)
        django_field_patterns = ['Field(', 'ForeignKey(', 'CharField(',
                               'IntegerField(', 'BooleanField(']
        for pattern in django_field_patterns:
            if pattern in line and full_access in line:
                return True
        
        # Type annotations (more specific check)
        if ': ' in line and ' = ' in line:
            colon_pos = line.find(': ')
            equals_pos = line.find(' = ')
            if colon_pos < equals_pos and full_access in line[colon_pos:equals_pos]:
                return True
        
        # Function return type annotations
        if '-> ' in line and full_access in line:
            return True
        
        return False
    
    def _is_risky_attribute_chain(self, full_access: str) -> bool:
        """
        Determine if this is a risky attribute chain (pure attribute access
        without method calls).
        """
        # If it contains common method names, it's likely safer
        safe_method_endings = [
            'get', 'filter', 'save', 'delete', 'create', 'update',
            'first', 'last', 'count', 'exists', 'is_valid'
        ]
        
        for method in safe_method_endings:
            if full_access.endswith(f'.{method}'):
                return False
        
        # Count dots - only flag very deep chains
        return full_access.count('.') >= 3 
"""
Rust Linter using clippy with comprehensive fallback

Provides Rust code analysis using clippy when available.
Falls back to comprehensive pattern-based analysis when Rust is not installed.
"""

import json
import subprocess
import tempfile
import os
import re
from typing import List, Dict, Any, Optional
from pathlib import Path


class RustLinter:
    """Rust code linter using clippy tool with robust fallback."""
    
    def __init__(self):
        self.clippy_command = None
        self.cargo_available = False
        self.clippy_available = self._check_clippy_installation()
        
        # Basic clippy configuration
        self.clippy_config = [
            '-W', 'clippy::all',           # Enable most lints
            '-W', 'clippy::correctness',   # Correctness issues
            '-W', 'clippy::style',         # Style improvements
            '-W', 'clippy::complexity',    # Code complexity
            '-W', 'clippy::perf',          # Performance hints
            '-W', 'clippy::suspicious',    # Suspicious patterns
        ]
        
        # Mapping from clippy lint groups to issue types
        self.lint_group_mapping = {
            'correctness': 'bug',
            'style': 'style', 
            'complexity': 'performance',
            'perf': 'performance',
            'restriction': 'best_practice',
            'suspicious': 'bug',
            'nursery': 'style',
            'pedantic': 'style',
        }
        
        # Rust naming conventions
        self.naming_patterns = {
            'snake_case': re.compile(r'^[a-z][a-z0-9_]*$'),
            'SCREAMING_SNAKE_CASE': re.compile(r'^[A-Z][A-Z0-9_]*$'),
            'PascalCase': re.compile(r'^[A-Z][a-zA-Z0-9]*$'),
        }
    
    def lint(self, filename: str, raw_code: str, 
             changed_lines: List[int]) -> List[Dict[str, Any]]:
        """
        Lint Rust code using clippy or comprehensive fallback analysis.
        
        Args:
            filename: Name of the file being analyzed
            raw_code: Full content of the file
            changed_lines: List of line numbers that were changed
            
        Returns:
            List of issues in standard format
        """
        if self.clippy_available:
            return self._run_clippy(filename, raw_code, changed_lines)
        else:
            return self._fallback_analysis(filename, raw_code, changed_lines)
    
    def _check_clippy_installation(self) -> bool:
        """Check clippy and cargo installation."""
        # Try different Rust/clippy installation methods
        rust_commands = [
            ['cargo', 'clippy', '--version'],    # Standard cargo clippy
            ['clippy-driver', '--version'],      # Direct clippy
            ['rustc', '--version'],              # Basic rust check
        ]
        
        for cmd in rust_commands:
            try:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                if result.returncode == 0:
                    if 'cargo' in cmd[0]:
                        self.cargo_available = True
                        self.clippy_command = ['cargo', 'clippy']
                    else:
                        self.clippy_command = ['clippy-driver']
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue
        
        return False
    
    def _run_clippy(self, filename: str, raw_code: str, 
                   changed_lines: List[int]) -> List[Dict[str, Any]]:
        """Run clippy and parse results."""
        temp_dir = None
        
        try:
            # Create temporary Cargo project
            temp_dir = tempfile.mkdtemp()
            
            # Create Cargo.toml
            cargo_toml = os.path.join(temp_dir, 'Cargo.toml')
            with open(cargo_toml, 'w', encoding='utf-8') as f:
                f.write("""[package]
name = "temp_analysis"
version = "0.1.0"
edition = "2021"

[dependencies]
""")
            
            # Create src directory and main.rs
            src_dir = os.path.join(temp_dir, 'src')
            os.makedirs(src_dir)
            
            main_rs = os.path.join(src_dir, 'main.rs')
            with open(main_rs, 'w', encoding='utf-8') as f:
                # Wrap code in main function if it's not a complete program
                if 'fn main(' not in raw_code and 'fn main()' not in raw_code:
                    f.write(f'fn main() {{\n{raw_code}\n}}')
                else:
                    f.write(raw_code)
            
            # Run clippy
            result = subprocess.run(
                self.clippy_command + [
                    '--message-format', 'json',
                    '--'
                ] + self.clippy_config,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return self._parse_clippy_output(
                result.stdout, changed_lines
            )
                    
        except Exception as e:
            print(f'Error running clippy: {e}')
            return self._fallback_analysis(filename, raw_code, changed_lines)
        finally:
            # Clean up temp directory
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                try:
                    shutil.rmtree(temp_dir)
                except OSError as e:
                    print(f'Warning: Could not delete temp dir {temp_dir}: {e}')
    
    def _parse_clippy_output(self, output: str, 
                            changed_lines: List[int]) -> List[Dict[str, Any]]:
        """Parse clippy JSON output and convert to standard format."""
        if not output.strip():
            return []
        
        issues = []
        
        # Clippy outputs one JSON object per line
        for line in output.strip().split('\n'):
            if not line.strip():
                continue
                
            try:
                clippy_msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            
            # Only process compiler messages
            if clippy_msg.get('reason') != 'compiler-message':
                continue
                
            message = clippy_msg.get('message', {})
            if not message:
                continue
            
            # Extract line number
            spans = message.get('spans', [])
            if not spans:
                continue
                
            primary_span = next((s for s in spans if s.get('is_primary')), spans[0])
            line_number = primary_span.get('line_start', 0)
            
            # Only include issues on changed lines
            if changed_lines and line_number not in changed_lines:
                continue
            
            # Determine issue type from lint code
            code = message.get('code', {}).get('code', '')
            issue_type = self._determine_clippy_issue_type(code)
            
            issues.append({
                'type': issue_type,
                'line': line_number,
                'description': message.get('message', 'Unknown clippy issue'),
                'suggestion': self._generate_clippy_suggestion(code, message.get('message', ''))
            })
        
        return issues
    
    def _determine_clippy_issue_type(self, lint_code: str) -> str:
        """Determine issue type based on clippy lint code."""
        if not lint_code:
            return 'style'
        
        # Extract lint group from code like "clippy::correctness"
        if '::' in lint_code:
            group = lint_code.split('::')[1].split('_')[0]  # Get first part after ::
            return self.lint_group_mapping.get(group, 'style')
        
        return 'style'
    
    def _generate_clippy_suggestion(self, lint_code: str, message: str) -> str:
        """Generate helpful suggestion based on clippy lint code."""
        suggestions = {
            'clippy::unwrap_used': 'Use proper error handling instead of unwrap()',
            'clippy::panic_in_result_fn': 'Return an error instead of panicking',
            'clippy::clone_on_ref_ptr': 'Avoid unnecessary cloning of reference-counted types',
            'clippy::redundant_clone': 'Remove unnecessary clone() call',
            'clippy::needless_collect': 'Use iterator directly instead of collecting',
        }
        
        return suggestions.get(lint_code, f'Clippy suggestion: {message}')
    
    def _fallback_analysis(self, filename: str, raw_code: str, 
                          changed_lines: List[int]) -> List[Dict[str, Any]]:
        """
        Comprehensive fallback analysis when clippy is not available.
        Performs pattern-based Rust code analysis.
        """
        issues = []
        lines = raw_code.split('\n')
        
        # Track context
        in_unsafe_block = False
        in_function = False
        current_function = None
        
        for i, line in enumerate(lines, 1):
            if changed_lines and i not in changed_lines:
                continue
            
            stripped = line.strip()
            
            # Track unsafe blocks
            if 'unsafe' in stripped and '{' in stripped:
                in_unsafe_block = True
            elif in_unsafe_block and stripped == '}':
                in_unsafe_block = False
            
            # Track functions
            fn_match = re.match(r'^\s*fn\s+(\w+)', stripped)
            if fn_match:
                in_function = True
                current_function = fn_match.group(1)
            
            # Basic style checks
            if len(line) > 100:  # Rust convention is usually 100
                issues.append({
                    'type': 'style',
                    'line': i,
                    'description': f'Line too long ({len(line)} > 100 characters)',
                    'suggestion': 'Break line into multiple lines'
                })
            
            # Check for panic and unwrap usage
            if re.search(r'\b(panic!|unwrap\(\)|expect\("[^"]*"\))', stripped):
                if 'unwrap()' in stripped:
                    issues.append({
                        'type': 'bug',
                        'line': i,
                        'description': 'unwrap() can cause panic',
                        'suggestion': 'Use match, if let, or ? operator for error handling'
                    })
                elif 'panic!' in stripped:
                    issues.append({
                        'type': 'bug',
                        'line': i,
                        'description': 'panic! can crash the program',
                        'suggestion': 'Use Result type or proper error handling'
                    })
            
            # Check for debugging statements
            if re.search(r'\b(println!|dbg!|eprintln!)', stripped):
                issues.append({
                    'type': 'style',
                    'line': i,
                    'description': 'Debug print statement found',
                    'suggestion': 'Remove debug prints before production'
                })
            
            # Check for unsafe usage
            if in_unsafe_block and any(pattern in stripped for pattern in ['*mut', '*const', 'transmute']):
                issues.append({
                    'type': 'best_practice',
                    'line': i,
                    'description': 'Unsafe operation detected',
                    'suggestion': 'Ensure unsafe code is properly documented and justified'
                })
            
            # Check for inefficient string operations
            if re.search(r'\+.*&str|String::from.*\+', stripped):
                issues.append({
                    'type': 'performance',
                    'line': i,
                    'description': 'Inefficient string concatenation',
                    'suggestion': 'Use format! macro or String::push_str for better performance'
                })
            
            # Check for unnecessary clones
            if '.clone()' in stripped and not ('Arc' in stripped or 'Rc' in stripped):
                issues.append({
                    'type': 'performance',
                    'line': i,
                    'description': 'Potentially unnecessary clone()',
                    'suggestion': 'Consider using references or borrowing instead of cloning'
                })
            
            # Check naming conventions
            # Variable declarations
            let_match = re.match(r'^\s*let\s+(\w+)', stripped)
            if let_match:
                var_name = let_match.group(1)
                if not self.naming_patterns['snake_case'].match(var_name):
                    issues.append({
                        'type': 'style',
                        'line': i,
                        'description': f'Variable "{var_name}" should use snake_case',
                        'suggestion': 'Use snake_case for variable names'
                    })
            
            # Function declarations  
            if fn_match:
                func_name = fn_match.group(1)
                if not self.naming_patterns['snake_case'].match(func_name):
                    issues.append({
                        'type': 'style',
                        'line': i,
                        'description': f'Function "{func_name}" should use snake_case',
                        'suggestion': 'Use snake_case for function names'
                    })
            
            # Struct/Enum declarations
            struct_match = re.match(r'^\s*(struct|enum)\s+(\w+)', stripped)
            if struct_match:
                type_name = struct_match.group(2)
                if not self.naming_patterns['PascalCase'].match(type_name):
                    issues.append({
                        'type': 'style',
                        'line': i,
                        'description': f'{struct_match.group(1).title()} "{type_name}" should use PascalCase',
                        'suggestion': 'Use PascalCase for type names'
                    })
            
            # Check for unhandled Results
            if 'Result<' in stripped and '.unwrap()' not in stripped and '?' not in stripped:
                # Look ahead to see if error is handled
                next_lines = lines[i:i+3] if i < len(lines) - 2 else lines[i:]
                has_error_handling = any(
                    'match' in l or 'if let' in l or '?' in l 
                    for l in next_lines
                )
                if not has_error_handling:
                    issues.append({
                        'type': 'best_practice',
                        'line': i,
                        'description': 'Result type not properly handled',
                        'suggestion': 'Use match, if let, or ? operator to handle Result'
                    })
            
            # Check for TODO/FIXME/HACK comments
            if re.search(r'//.*\b(TODO|FIXME|HACK|XXX)\b', stripped, re.I):
                issues.append({
                    'type': 'style',
                    'line': i,
                    'description': 'TODO/FIXME comment found',
                    'suggestion': 'Address TODO items before production'
                })
            
            # Check for missing documentation on public items
            if (stripped.startswith('pub fn ') or 
                stripped.startswith('pub struct ') or 
                stripped.startswith('pub enum ')):
                # Check if previous line has documentation
                prev_line = lines[i-2].strip() if i > 1 else ''
                if not prev_line.startswith('///') and not prev_line.startswith('#[doc'):
                    issues.append({
                        'type': 'style',
                        'line': i,
                        'description': 'Public item missing documentation',
                        'suggestion': 'Add /// documentation for public items'
                    })
        
        return issues 
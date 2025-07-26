"""
BaseAgent Implementation for Code Review

The BaseAgent class acts as the orchestrator for code analysis. It accepts 
the final_payload from format_pr_data_to_pass_to_agent() and runs analyzers
over each file in the PR.
"""

import re
import uuid
from typing import List, Dict, Any, Optional

from .analyzers.code_quality import CodeQualityAnalyzer


class BaseAgent:
    """
    Main orchestrator for code review analysis.
    
    Accepts the final_payload from pr_handlers.py and dispatches to analyzers,
    then formats the results according to the project specification.
    """
    
    def __init__(self, analyzers: Optional[List] = None, final_payload: Dict[str, Any] = None):
        """
        Initialize BaseAgent with a list of analyzers and PR data.
        
        Args:
            analyzers: List of analyzer instances. Defaults to CodeQualityAnalyzer.
            final_payload: The structured data from format_pr_data_to_pass_to_agent()
        """
        if final_payload is None:
            raise ValueError('final_payload is required for BaseAgent initialization')
            
        self.final_payload = final_payload
        self.pr_metadata = self._extract_pr_metadata()
        self.files_data = self._extract_files_data()
        self.existing_context = self._extract_existing_context()
        self.analyzers = analyzers or [CodeQualityAnalyzer()]
    
    def review(self) -> Dict[str, Any]:
        """
        Review a pull request by analyzing all files with all analyzers.
        
        Args:
            final_payload: The structured data from format_pr_data_to_pass_to_agent()
                          containing summary, file_info, existing_reviews, existing_comments
            
        Returns:
            Structured review results matching projectcontext.mdc format
        """
        # Segregate the payload data into respective components

        
        # Analyze each file
        file_reviews = []
        
        for file_info in self.files_data:
            # Extract changed line numbers from patch
            changed_lines = self._extract_changed_lines(file_info.get('patch', ''))
            
            # Extract actual code content from patch (temporary solution)
            raw_code = self._extract_code_from_patch(file_info.get('patch', ''))
            
            # Collect issues from all analyzers for this file
            issues = []
            for analyzer in self.analyzers:
                file_issues = analyzer.analyze(
                    filename=file_info['file_name'],
                    patch=file_info.get('patch', ''),
                    raw_code=raw_code,
                    changed_lines=changed_lines
                )
                issues.extend(file_issues)
            
            # Add file review to results
            file_reviews.append({
                'name': file_info['file_name'],
                'issues': issues
            })
        
        return self._format_output(file_reviews, self.pr_metadata)
    
    def _extract_pr_metadata(self) -> Dict[str, Any]:
        """
        Extract PR metadata from the final_payload.
        
        Args:
            self.final_payload: The payload from format_pr_data_to_pass_to_agent()
            
        Returns:
            Dictionary containing PR metadata
        """
        summary = self.final_payload.get('summary', {})
        
        return {
            'pr_number': summary.get('pr_number'),
            'pr_title': summary.get('pr_title'),
            'pr_body': summary.get('pr_body'),
            'language': summary.get('language', 'Unknown'),
            'state': summary.get('state'),
            'author_association': summary.get('author_association'),
            'pr_created_at': summary.get('pr_created_at'),
            'pr_updated_at': summary.get('pr_updated_at'),
            'commits': summary.get('commits', []),
            'stats': summary.get('stats', {})
        }
    
    def _extract_files_data(self) -> List[Dict[str, Any]]:
        """
        Extract file information from the final_payload.
        
        Args:
            self.final_payload: The payload from format_pr_data_to_pass_to_agent()
            
        Returns:
            List of file dictionaries
        """
        return self.final_payload.get('file_info', [])
    
    def _extract_existing_context(self) -> Dict[str, Any]:
        """
        Extract existing reviews and comments from the final_payload.
        
        Args:
            self.final_payload: The payload from format_pr_data_to_pass_to_agent()
            
        Returns:
            Dictionary containing existing reviews and comments
        """
        return {
            'existing_reviews': self.final_payload.get('existing_reviews', []),
            'existing_comments': self.final_payload.get('existing_comments', [])
        }
    
    def _extract_changed_lines(self, patch: str) -> List[int]:
        """
        Extract line numbers that were changed from a GitHub patch.
        
        Args:
            patch: Git patch content from GitHub API
            
        Returns:
            List of line numbers that were added or modified
        """
        if not patch:
            return []
        
        changed_lines = []
        current_line = 0
        
        for line in patch.split('\n'):
            # Look for hunk headers like @@ -10,7 +10,8 @@
            hunk_match = re.match(r'^@@ -\d+,?\d* \+(\d+),?\d* @@', line)
            if hunk_match:
                current_line = int(hunk_match.group(1)) - 1
                continue
            
            # Track line numbers for additions and unchanged lines
            if line.startswith('+') and not line.startswith('+++'):
                # This is an added line
                current_line += 1
                changed_lines.append(current_line)
            elif line.startswith('-') and not line.startswith('---'):
                # This is a deleted line (don't increment current_line)
                pass
            elif not line.startswith('\\'):
                # This is an unchanged line or context line
                current_line += 1
        
        return sorted(list(set(changed_lines)))
    
    def _extract_code_from_patch(self, patch: str) -> str:
        """
        Extract the actual code content from a git patch.
        
        This is a temporary solution that extracts added/modified lines
        from the patch. Ideally, we should fetch the full file content
        from GitHub API.
        
        Args:
            patch: Git patch content from GitHub API
            
        Returns:
            Extracted code content (added lines only)
        """
        if not patch:
            return ''
        
        code_lines = []
        
        for line in patch.split('\n'):
            # Skip diff headers and context
            if (line.startswith('@@') or 
                line.startswith('+++') or 
                line.startswith('---') or
                line.startswith('\\') or
                line.startswith('diff')):
                continue
            
            # Extract added lines (remove the + prefix)
            if line.startswith('+'):
                code_lines.append(line[1:])  # Remove the '+' prefix
            # Include unchanged context lines (no prefix)
            elif not line.startswith('-'):
                # Only include if it doesn't start with - (deleted lines)
                if line:  # Skip empty lines that might be diff artifacts
                    code_lines.append(line)
        
        return '\n'.join(code_lines)
    
    def _format_output(self, file_reviews: List[Dict[str, Any]], 
                      pr_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the analysis results according to projectcontext.mdc specification.
        
        Args:
            file_reviews: List of file review results
            pr_metadata: PR metadata for context
            
        Returns:
            Formatted output matching the required structure
        """
        # Calculate summary statistics
        total_issues = sum(len(f['issues']) for f in file_reviews)
        critical_issues = sum(
            1 for f in file_reviews 
            for issue in f['issues'] 
            if issue['type'] == 'bug'
        )
        
        return {
            'task_id': str(uuid.uuid4()),
            'status': 'completed',
            'results': {
                'files': file_reviews,
                'summary': {
                    'total_files': len(file_reviews),
                    'total_issues': total_issues,
                    'critical_issues': critical_issues
                }
            }
        }
    
    def add_analyzer(self, analyzer):
        """Add an analyzer to the list of analyzers."""
        self.analyzers.append(analyzer)
    
    def remove_analyzer(self, analyzer_class):
        """Remove all analyzers of a specific class."""
        self.analyzers = [a for a in self.analyzers 
                         if not isinstance(a, analyzer_class)] 
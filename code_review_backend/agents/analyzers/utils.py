"""
Analyzer Utilities

Common utilities and helper functions shared across analyzer agents.
Reduces code duplication and ensures consistency.
"""

from typing import List, Dict, Any, Callable, Optional
from abc import ABC, abstractmethod


def filter_issues_by_lines(issues: List[Dict[str, Any]], 
                          target_lines: List[int]) -> List[Dict[str, Any]]:
    """Filter issues to only those on specified lines."""
    if not target_lines:
        return []
    
    filtered_issues = []
    target_lines_set = set(target_lines)
    
    for issue in issues:
        if issue.get('line') in target_lines_set:
            filtered_issues.append(issue)
    
    return filtered_issues


def deduplicate_issues(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate issues based on line number and description similarity."""
    if not issues:
        return []
    
    deduplicated = []
    seen_combinations = set()
    
    for issue in issues:
        # Create a signature for deduplication
        signature = (
            issue.get('line', 0),
            issue.get('description', '')[:50].lower()  # First 50 chars
        )
        
        if signature not in seen_combinations:
            seen_combinations.add(signature)
            deduplicated.append(issue)
    
    return deduplicated


def is_generic_issue(description: str, 
                    generic_phrases: List[str]) -> bool:
    """Check if the issue description is too generic to be useful."""
    description_lower = description.lower()
    return any(phrase in description_lower for phrase in generic_phrases)


def post_process_issues(issues: List[Dict[str, Any]], 
                       changed_lines: List[int],
                       generic_phrases: List[str]) -> List[Dict[str, Any]]:
    """
    Post-process LLM-generated issues with common filtering and validation.
    
    Args:
        issues: Raw issues from LLM
        changed_lines: Line numbers that were changed
        generic_phrases: List of phrases that indicate generic/unhelpful issues
        
    Returns:
        Filtered and deduplicated issues
    """
    processed_issues = []
    changed_lines_set = set(changed_lines)
    
    for issue in issues:
        # Ensure issue is on a changed line
        if issue.get('line') not in changed_lines_set:
            continue
        
        # Skip issues with very generic descriptions
        description = issue.get('description', '')
        if is_generic_issue(description, generic_phrases):
            continue
        
        # Ensure required fields are present
        if not all(key in issue for key in 
                  ['line', 'description', 'suggestion']):
            continue
        
        processed_issues.append(issue)
    
    return deduplicate_issues(processed_issues)


def analyze_large_file_chunks(code: str, 
                             changed_lines: List[int],
                             analysis_func: Callable,
                             context_size: int = 5) -> List[Dict[str, Any]]:
    """
    Handle analysis of large files by focusing on changed regions.
    
    Args:
        code: Full code content
        changed_lines: Line numbers that were changed
        analysis_func: Function to call for analyzing each chunk
        context_size: Number of lines of context around each change
        
    Returns:
        Combined analysis results from all chunks
    """
    code_lines = code.split('\n')
    chunks = []
    
    for line_num in changed_lines:
        start_line = max(1, line_num - context_size)
        end_line = min(len(code_lines), line_num + context_size)
        
        chunk_lines = code_lines[start_line-1:end_line]
        chunk_code = '\n'.join(chunk_lines)
        
        # Analyze this chunk with adjusted line numbers
        chunk_issues = analysis_func(
            code=chunk_code,
            changed_lines=[line_num - start_line + 1]
        )
        
        # Adjust line numbers back to original file
        for issue in chunk_issues:
            issue['line'] = issue['line'] + start_line - 1
        
        chunks.extend(chunk_issues)
    
    return deduplicate_issues(chunks)


class LLMAnalyzerMixin:
    """
    Mixin class providing common functionality for LLM-based analyzers.
    
    This mixin provides standard methods that are shared across all
    LLM analyzer agents to reduce code duplication.
    """
    
    # Subclasses should define their specific generic phrases
    GENERIC_PHRASES: List[str] = []
    
    def filter_issues_by_lines(self, issues: List[Dict[str, Any]], 
                              target_lines: List[int]) -> List[Dict[str, Any]]:
        """Filter issues to only those on specified lines."""
        return filter_issues_by_lines(issues, target_lines)
    
    def post_process_issues(self, issues: List[Dict[str, Any]], 
                           changed_lines: List[int]) -> List[Dict[str, Any]]:
        """Post-process LLM-generated issues."""
        return post_process_issues(issues, changed_lines, self.GENERIC_PHRASES)
    
    def deduplicate_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate issues."""
        return deduplicate_issues(issues)
    
    def is_generic_issue(self, description: str) -> bool:
        """Check if the issue description is too generic."""
        return is_generic_issue(description, self.GENERIC_PHRASES)
    
    def analyze_with_custom_prompt(self, custom_prompt: str) -> str:
        """
        Analyze code with a custom prompt.
        
        Args:
            custom_prompt: Custom analysis prompt
            
        Returns:
            Raw LLM response
        """
        return self.llm_service.generate_custom_analysis(custom_prompt)
    
    @abstractmethod
    def _get_llm_analysis_method(self):
        """Return the appropriate LLM service method for this analyzer type."""
        pass
    
    def analyze_large_file(self, filename: str, code: str, 
                          changed_lines: List[int], **kwargs) -> List[Dict[str, Any]]:
        """
        Handle analysis of large files by focusing on changed regions.
        
        This method uses the template method pattern - subclasses provide
        the specific LLM analysis method via _get_llm_analysis_method().
        """
        def analysis_func(code: str, changed_lines: List[int]) -> List[Dict[str, Any]]:
            # Get the appropriate LLM analysis method
            llm_method = self._get_llm_analysis_method()
            
            # Call with all the original parameters plus the chunk-specific ones
            return llm_method(
                filename=filename,
                code=code,
                changed_lines=changed_lines,
                **{k: self.filter_issues_by_lines(v or [], changed_lines) 
                   if isinstance(v, list) and k.endswith('_issues') 
                   else v for k, v in kwargs.items()}
            )
        
        return analyze_large_file_chunks(code, changed_lines, analysis_func)


# Generic phrase constants for different analyzer types
BUG_GENERIC_PHRASES = [
    'might have an issue',
    'could be improved',
    'may need review',
    'potential problem',
    'unclear code'
]

PERFORMANCE_GENERIC_PHRASES = [
    'might be slow',
    'could be optimized',
    'may affect performance',
    'potential optimization',
    'unclear performance'
]

BEST_PRACTICES_GENERIC_PHRASES = [
    'could be improved',
    'may be better',
    'consider refactoring',
    'unclear naming',
    'general improvement'
] 
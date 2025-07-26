"""
LLM-based Bug Detection Agent

Uses Large Language Models to detect potential bugs and logic errors
in code changes. Integrates with the central LLM service for provider flexibility.
"""

from typing import List, Dict, Any, Optional
from services.llm_service import LLMService, LLMProvider


class LLMBugAgent:
    """
    LLM-powered bug detection agent.
    
    Uses advanced language models to identify potential bugs, logic errors,
    and correctness issues that static analysis might miss.
    """
    
    def __init__(self, llm_provider: LLMProvider = LLMProvider.GEMINI,
                 api_key: Optional[str] = None):
        """
        Initialize the LLM bug detection agent.
        
        Args:
            llm_provider: The LLM provider to use for analysis
            api_key: API key for the LLM provider
        """
        self.llm_service = LLMService(provider=llm_provider, api_key=api_key)
    
    def analyze(self, filename: str, code: str, changed_lines: List[int],
                patch: str = '', lint_issues: List[Dict[str, Any]] = None,
                heuristic_issues: List[Dict[str, Any]] = None
                ) -> List[Dict[str, Any]]:
        """
        Analyze code for potential bugs using LLM.
        
        Args:
            filename: Name of the file being analyzed
            code: Full code content or code fragment  
            changed_lines: Line numbers that were changed in the PR
            patch: Git patch content (for additional context)
            lint_issues: Existing lint issues for context
            heuristic_issues: Issues found by static heuristics
            
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
        # Skip analysis if no changed lines
        if not changed_lines:
            return []
        
        # Skip very large files to avoid token limits
        if len(code.split('\n')) > 500:
            return self._analyze_large_file(
                filename, code, changed_lines, lint_issues, heuristic_issues
            )
        
        # Filter existing issues to only those on changed lines for context
        relevant_lint_issues = self._filter_issues_by_lines(
            lint_issues or [], changed_lines
        )
        relevant_heuristic_issues = self._filter_issues_by_lines(
            heuristic_issues or [], changed_lines
        )
        
        # Use LLM service for analysis
        llm_issues = self.llm_service.analyze_code_for_bugs(
            filename=filename,
            code=code,
            changed_lines=changed_lines,
            lint_issues=relevant_lint_issues,
            heuristic_issues=relevant_heuristic_issues
        )
        
        # Post-process results
        return self._post_process_issues(llm_issues, changed_lines)
    
    def _filter_issues_by_lines(self, issues: List[Dict[str, Any]], 
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
    
    def _analyze_large_file(self, filename: str, code: str, 
                           changed_lines: List[int],
                           lint_issues: List[Dict[str, Any]] = None,
                           heuristic_issues: List[Dict[str, Any]] = None
                           ) -> List[Dict[str, Any]]:
        """
        Handle analysis of large files by focusing on changed regions.
        
        For large files, extract relevant code chunks around changed lines
        to avoid LLM token limits.
        """
        code_lines = code.split('\n')
        
        # Extract chunks around changed lines (±5 lines context)
        chunks = []
        context_size = 5
        
        for line_num in changed_lines:
            start_line = max(1, line_num - context_size)
            end_line = min(len(code_lines), line_num + context_size)
            
            chunk_lines = code_lines[start_line-1:end_line]
            chunk_code = '\n'.join(chunk_lines)
            
            # Analyze this chunk
            chunk_issues = self.llm_service.analyze_code_for_bugs(
                filename=filename,
                code=chunk_code,
                changed_lines=[line_num - start_line + 1],  # Adjust line number
                lint_issues=self._filter_issues_by_lines(
                    lint_issues or [], [line_num]
                ),
                heuristic_issues=self._filter_issues_by_lines(
                    heuristic_issues or [], [line_num]
                )
            )
            
            # Adjust line numbers back to original file
            for issue in chunk_issues:
                issue['line'] = issue['line'] + start_line - 1
            
            chunks.extend(chunk_issues)
        
        return self._deduplicate_issues(chunks)
    
    def _post_process_issues(self, issues: List[Dict[str, Any]], 
                           changed_lines: List[int]) -> List[Dict[str, Any]]:
        """
        Post-process LLM-generated issues.
        
        Applies filtering and validation to ensure quality results.
        """
        processed_issues = []
        changed_lines_set = set(changed_lines)
        
        for issue in issues:
            # Ensure issue is on a changed line
            if issue.get('line') not in changed_lines_set:
                continue
            
            # Skip issues with very generic descriptions
            description = issue.get('description', '').lower()
            if self._is_generic_issue(description):
                continue
            
            # Ensure required fields are present
            if not all(key in issue for key in ['line', 'description', 'suggestion']):
                continue
            
            processed_issues.append(issue)
        
        return self._deduplicate_issues(processed_issues)
    
    def _is_generic_issue(self, description: str) -> bool:
        """Check if the issue description is too generic to be useful."""
        generic_phrases = [
            'might have an issue',
            'could be improved',
            'may need review',
            'potential problem',
            'unclear code'
        ]
        
        return any(phrase in description for phrase in generic_phrases)
    
    def _deduplicate_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
    
    def analyze_with_custom_prompt(self, custom_prompt: str) -> str:
        """
        Analyze code with a custom prompt for specialized use cases.
        
        Args:
            custom_prompt: Custom analysis prompt
            
        Returns:
            Raw LLM response
        """
        return self.llm_service.generate_custom_analysis(custom_prompt) 
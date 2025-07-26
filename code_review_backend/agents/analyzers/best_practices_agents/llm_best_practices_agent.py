"""
LLM-based Best Practices Analysis Agent

Uses Large Language Models to identify opportunities for improving code
maintainability, readability, and adherence to idiomatic development standards.
Integrates with the central LLM service for provider flexibility.
"""

from typing import List, Dict, Any, Optional
from services.llm_service import LLMService, LLMProvider
from ..utils import (
    filter_issues_by_lines, 
    post_process_issues, 
    BEST_PRACTICES_GENERIC_PHRASES
)


class LLMBestPracticesAgent:
    """
    LLM-powered best practices analysis agent.
    
    Uses advanced language models to identify opportunities for improving
    code maintainability, readability, and adherence to language-specific
    idioms and conventions.
    """
    
    def __init__(self, llm_provider: LLMProvider = LLMProvider.GEMINI,
                 api_key: Optional[str] = None):
        """
        Initialize the LLM best practices analysis agent.
        
        Args:
            llm_provider: The LLM provider to use for analysis
            api_key: API key for the LLM provider
        """
        self.llm_service = LLMService(provider=llm_provider, api_key=api_key)
    
    def analyze(self, filename: str, code: str, changed_lines: List[int],
                patch: str = '', language: str = 'Unknown',
                lint_issues: List[Dict[str, Any]] = None,
                bug_issues: List[Dict[str, Any]] = None,
                perf_issues: List[Dict[str, Any]] = None
                ) -> List[Dict[str, Any]]:
        """
        Analyze code for best practices adherence using LLM.
        
        Args:
            filename: Name of the file being analyzed
            code: Full code content or code fragment  
            changed_lines: Line numbers that were changed in the PR
            patch: Git patch content (for additional context)
            language: Programming language of the file
            lint_issues: Existing lint issues for context
            bug_issues: Issues found by bug analysis for context
            perf_issues: Issues found by performance analysis for context
            
        Returns:
            List of best practices issues in standard format:
            [
                {
                    "type": "best_practice",
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
                filename, code, changed_lines, language, 
                lint_issues, bug_issues, perf_issues
            )
        
        # Filter existing issues to only those on changed lines for context
        relevant_lint_issues = filter_issues_by_lines(
            lint_issues or [], changed_lines
        )
        relevant_bug_issues = filter_issues_by_lines(
            bug_issues or [], changed_lines
        )
        relevant_perf_issues = filter_issues_by_lines(
            perf_issues or [], changed_lines
        )
        
        # Use LLM service for best practices analysis
        bp_issues = self.llm_service.analyze_code_for_best_practices(
            filename=filename,
            code=code,
            changed_lines=changed_lines,
            language=language,
            lint_issues=relevant_lint_issues,
            bug_issues=relevant_bug_issues,
            perf_issues=relevant_perf_issues
        )
        
        # Post-process results
        return post_process_issues(bp_issues, changed_lines, BEST_PRACTICES_GENERIC_PHRASES)
    

    
    def _analyze_large_file(self, filename: str, code: str, 
                           changed_lines: List[int], language: str,
                           lint_issues: List[Dict[str, Any]] = None,
                           bug_issues: List[Dict[str, Any]] = None,
                           perf_issues: List[Dict[str, Any]] = None
                           ) -> List[Dict[str, Any]]:
        """
        Handle analysis of large files by focusing on changed regions.
        
        For large files, extract relevant code chunks around changed lines
        to avoid LLM token limits.
        """
        from ..utils import analyze_large_file_chunks
        
        def analysis_func(code: str, changed_lines: List[int]) -> List[Dict[str, Any]]:
            return self.llm_service.analyze_code_for_best_practices(
                filename=filename,
                code=code,
                changed_lines=changed_lines,
                language=language,
                lint_issues=filter_issues_by_lines(lint_issues or [], changed_lines),
                bug_issues=filter_issues_by_lines(bug_issues or [], changed_lines),
                perf_issues=filter_issues_by_lines(perf_issues or [], changed_lines)
            )
        
        return analyze_large_file_chunks(code, changed_lines, analysis_func)
    

    

    

    
    def analyze_with_custom_prompt(self, custom_prompt: str) -> str:
        """
        Analyze code with a custom prompt for specialized best practices analysis.
        
        Args:
            custom_prompt: Custom analysis prompt
            
        Returns:
            Raw LLM response
        """
        return self.llm_service.generate_custom_analysis(custom_prompt) 
"""
Analysis Pipeline

Implements a preprocessor/post-processor architecture that separates 
data processing from domain-specific analysis logic.
"""

from typing import List, Dict, Any, Optional, Callable
from .utils import (
    filter_issues_by_lines,
    analyze_large_file_chunks, 
    post_process_issues,
    deduplicate_issues,
    BUG_GENERIC_PHRASES,
    PERFORMANCE_GENERIC_PHRASES,
    BEST_PRACTICES_GENERIC_PHRASES
)


class AnalysisPreprocessor:
    """
    Preprocesses input data before passing to analyzers.
    
    Handles all common data preparation tasks that would otherwise
    be duplicated across multiple analyzers.
    """
    
    @staticmethod
    def preprocess_file_data(filename: str, code: str, changed_lines: List[int],
                           language: str = 'Unknown', 
                           context_issues: Dict[str, List[Dict[str, Any]]] = None
                           ) -> Dict[str, Any]:
        """
        Preprocess file data for analysis.
        
        Args:
            filename: Name of the file being analyzed
            code: Full code content
            changed_lines: Line numbers that were changed in the PR
            language: Programming language of the file
            context_issues: Existing issues from other analyzers for context
            
        Returns:
            Preprocessed data ready for analyzer consumption
        """
        context_issues = context_issues or {}
        
        # Determine if file needs chunking
        is_large_file = len(code.split('\n')) > 500
        
        # Filter context issues to only changed lines
        filtered_context = {}
        for issue_type, issues in context_issues.items():
            filtered_context[issue_type] = filter_issues_by_lines(
                issues, changed_lines
            )
        
        return {
            'filename': filename,
            'code': code,
            'changed_lines': changed_lines,
            'language': language,
            'is_large_file': is_large_file,
            'context_issues': filtered_context,
            'metadata': {
                'total_lines': len(code.split('\n')),
                'changed_line_count': len(changed_lines),
                'language': language
            }
        }
    
    @staticmethod
    def handle_large_file_analysis(preprocessed_data: Dict[str, Any],
                                 analysis_function: Callable
                                 ) -> List[Dict[str, Any]]:
        """
        Handle large file analysis using chunking strategy.
        
        Args:
            preprocessed_data: Data from preprocess_file_data()
            analysis_function: Function to call for analyzing each chunk
            
        Returns:
            Combined analysis results from all chunks
        """
        if not preprocessed_data['is_large_file']:
            # For normal files, call analysis function directly
            return analysis_function(preprocessed_data)
        
        # For large files, use chunking
        def chunk_analysis_func(code: str, changed_lines: List[int]) -> List[Dict[str, Any]]:
            # Create chunk-specific preprocessed data
            chunk_data = preprocessed_data.copy()
            chunk_data.update({
                'code': code,
                'changed_lines': changed_lines,
                'is_large_file': False  # Chunks are small by definition
            })
            return analysis_function(chunk_data)
        
        return analyze_large_file_chunks(
            preprocessed_data['code'],
            preprocessed_data['changed_lines'],
            chunk_analysis_func
        )


class AnalysisPostprocessor:
    """
    Post-processes analysis results from multiple analyzers.
    
    Handles deduplication, filtering, and final result formatting.
    """
    
    # Generic phrase mappings for different analyzer types
    GENERIC_PHRASE_MAP = {
        'bug': BUG_GENERIC_PHRASES,
        'performance': PERFORMANCE_GENERIC_PHRASES,
        'best_practice': BEST_PRACTICES_GENERIC_PHRASES
    }
    
    @staticmethod
    def process_analyzer_results(analyzer_results: Dict[str, List[Dict[str, Any]]],
                               changed_lines: List[int]
                               ) -> List[Dict[str, Any]]:
        """
        Process and combine results from multiple analyzers.
        
        Args:
            analyzer_results: Dict mapping analyzer_type -> list of issues
            changed_lines: Line numbers that were changed
            
        Returns:
            Processed and deduplicated issues
        """
        all_processed_issues = []
        
        # Process each analyzer's results with their specific generic phrases
        for analyzer_type, issues in analyzer_results.items():
            generic_phrases = AnalysisPostprocessor.GENERIC_PHRASE_MAP.get(
                analyzer_type, []
            )
            
            processed_issues = post_process_issues(
                issues, changed_lines, generic_phrases
            )
            
            all_processed_issues.extend(processed_issues)
        
        # Final deduplication across all analyzers
        return deduplicate_issues(all_processed_issues)
    
    @staticmethod
    def validate_and_enrich_results(issues: List[Dict[str, Any]],
                                  metadata: Dict[str, Any]
                                  ) -> List[Dict[str, Any]]:
        """
        Final validation and enrichment of analysis results.
        
        Args:
            issues: Processed issues from analyzers
            metadata: File metadata for enrichment
            
        Returns:
            Validated and enriched issues
        """
        enriched_issues = []
        
        for issue in issues:
            # Validate required fields
            if not all(key in issue for key in ['line', 'description', 'suggestion', 'type']):
                continue
            
            # Enrich with metadata
            enriched_issue = issue.copy()
            enriched_issue.update({
                'confidence': issue.get('confidence', 'medium'),
                'file_language': metadata.get('language', 'Unknown'),
                'total_file_lines': metadata.get('total_lines', 0)
            })
            
            enriched_issues.append(enriched_issue)
        
        return enriched_issues


class AnalysisPipeline:
    """
    Main pipeline coordinator that orchestrates preprocessing, analysis, and post-processing.
    
    This class implements the new architecture where analyzers become pure domain logic
    and all common processing is handled by the pipeline.
    """
    
    def __init__(self, analyzers: Dict[str, Any]):
        """
        Initialize the pipeline with a set of analyzers.
        
        Args:
            analyzers: Dict mapping analyzer_type -> analyzer_instance
        """
        self.analyzers = analyzers
        self.preprocessor = AnalysisPreprocessor()
        self.postprocessor = AnalysisPostprocessor()
    
    def analyze_file(self, filename: str, code: str, changed_lines: List[int],
                    language: str = 'Unknown') -> List[Dict[str, Any]]:
        """
        Analyze a file using the complete pipeline.
        
        Args:
            filename: Name of the file being analyzed
            code: Full code content
            changed_lines: Line numbers that were changed
            language: Programming language of the file
            
        Returns:
            Processed analysis results from all analyzers
        """
        # Step 1: Preprocess the input data
        preprocessed_data = self.preprocessor.preprocess_file_data(
            filename, code, changed_lines, language
        )
        
        # Step 2: Run analyzers in sequence, building up context
        analyzer_results = {}
        context_issues = {}
        
        for analyzer_type, analyzer in self.analyzers.items():
            # Update preprocessed data with latest context
            preprocessed_data['context_issues'] = context_issues
            
            # Run the analyzer (handling large files automatically)
            issues = self.preprocessor.handle_large_file_analysis(
                preprocessed_data,
                lambda data: self._call_pure_analyzer(analyzer, data)
            )
            
            analyzer_results[analyzer_type] = issues
            
            # Add these results to context for next analyzer
            context_issues[analyzer_type] = issues
        
        # Step 3: Post-process all results together
        processed_issues = self.postprocessor.process_analyzer_results(
            analyzer_results, changed_lines
        )
        
        # Step 4: Final validation and enrichment
        final_issues = self.postprocessor.validate_and_enrich_results(
            processed_issues, preprocessed_data['metadata']
        )
        
        return final_issues
    
    def _call_pure_analyzer(self, analyzer: Any, 
                          preprocessed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Call an analyzer with preprocessed data.
        
        This method adapts the new pipeline to work with existing analyzer interfaces
        until they can be refactored to be pure domain logic.
        """
        # For now, adapt to existing analyzer interfaces
        # TODO: Refactor analyzers to accept preprocessed_data directly
        
        context = preprocessed_data['context_issues']
        
        if hasattr(analyzer, 'analyze'):
            # Determine analyzer type and call with appropriate parameters
            if 'bug' in analyzer.__class__.__name__.lower():
                return analyzer.analyze(
                    filename=preprocessed_data['filename'],
                    code=preprocessed_data['code'],
                    changed_lines=preprocessed_data['changed_lines'],
                    lint_issues=context.get('lint', []),
                    heuristic_issues=context.get('heuristic', [])
                )
            elif 'performance' in analyzer.__class__.__name__.lower():
                return analyzer.analyze(
                    filename=preprocessed_data['filename'],
                    code=preprocessed_data['code'],
                    changed_lines=preprocessed_data['changed_lines'],
                    language=preprocessed_data['language'],
                    lint_issues=context.get('lint', []),
                    bug_issues=context.get('bug', [])
                )
            elif 'best_practices' in analyzer.__class__.__name__.lower():
                return analyzer.analyze(
                    filename=preprocessed_data['filename'],
                    code=preprocessed_data['code'],
                    changed_lines=preprocessed_data['changed_lines'],
                    language=preprocessed_data['language'],
                    lint_issues=context.get('lint', []),
                    bug_issues=context.get('bug', []),
                    perf_issues=context.get('performance', [])
                )
        
        return [] 
"""
LangGraph-based Code Review Agent

This implementation uses LangGraph for sophisticated workflow orchestration,
state management, and multi-agent collaboration in code review analysis.
"""
import os
import uuid
from typing import List, Dict, Any, Optional, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from .analyzers.linters.python_linter import PythonLinter
from .analyzers.linters.js_linter import JSLinter
from .analyzers.linters.go_linter import GoLinter
from .analyzers.linters.rust_linter import RustLinter
from .analyzers.bug_heuristics.python_heuristics import PythonBugHeuristics
from .analyzers.bug_agents.llm_bug_agent import LLMBugAgent
from .analyzers.performance_agents.llm_performance_agent import LLMPerformanceAgent
from .analyzers.best_practices_agents.llm_best_practices_agent import LLMBestPracticesAgent
from .analyzers.utils import (
    filter_issues_by_lines,
    analyze_large_file_chunks,
    post_process_issues,
    deduplicate_issues
)


class CodeReviewState(TypedDict, total=False):
    """
    State schema for the LangGraph code review workflow.
    
    This state is maintained throughout the entire analysis process
    and gets updated by each node in the graph.
    
    total=False allows for optional fields and gradual state building.
    """
    # Input data
    pr_metadata: Dict[str, Any]
    files_data: List[Dict[str, Any]]
    existing_context: Dict[str, Any]
    
    # Current file being processed
    current_file: Optional[Dict[str, Any]]
    current_file_index: int
    
    # Analysis results per file
    file_results: Dict[str, List[Dict[str, Any]]]  # filename -> issues
    
    # Accumulated context for sequential analysis
    analysis_context: Dict[str, Any]
    
    # Final output
    final_results: Optional[Dict[str, Any]]
    
    # Workflow control
    error_message: Optional[str]
    completed_files: List[str]


class LangGraphCodeReviewAgent:
    """
    LangGraph-based code review agent that orchestrates multiple analyzers
    using a stateful graph workflow.
    """
    
    def __init__(self, final_payload: Dict[str, Any]):
        if final_payload is None:
            raise ValueError('final_payload is required for LangGraphCodeReviewAgent initialization')
            
        self.final_payload = final_payload
        
        # Initialize analyzers
        self.linters = {
            'python': PythonLinter(),
            'js': JSLinter(),
            'go': GoLinter(),
            'rust': RustLinter()
        }
        
        self.heuristics = {
            'python': PythonBugHeuristics()
        }
        
        self.llm_agents = {
            'bug': LLMBugAgent(),
            'performance': LLMPerformanceAgent(),
            'best_practices': LLMBestPracticesAgent()
        }
        
        # Build the LangGraph workflow
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build a simplified, recursion-free workflow."""
        workflow = StateGraph(CodeReviewState)
        
        # SIMPLIFIED: Only 3 nodes, no loops
        workflow.add_node('initialize', self._initialize_state)
        workflow.add_node('process_files', self._process_all_files)  # Process ALL files here
        workflow.add_node('format_results', self._format_results)
        
        # LINEAR FLOW: No conditional edges, no loops
        workflow.set_entry_point('initialize')
        workflow.add_edge('initialize', 'process_files')
        workflow.add_edge('process_files', 'format_results')
        workflow.add_edge('format_results', END)
        
        return workflow.compile()

    def _process_all_files(self, state: CodeReviewState) -> CodeReviewState:
        """Process all files in a single node - no recursion needed."""
        files_data = state.get('files_data', [])
        file_results = {}
        
        # Simple for loop - no graph recursion
        for index, file_info in enumerate(files_data):
            # Run complete analysis pipeline for this file
            issues = self._analyze_single_file(file_info)
            file_results[file_info['file_name']] = issues
        return {
            **state,
            'file_results': file_results
        }

    def _analyze_single_file(self, file_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze a single file through the complete pipeline."""
        filename = file_info['file_name']
        code = self._extract_code_from_patch(file_info.get('patch', ''))
        changed_lines = self._extract_changed_lines(file_info.get('patch', ''))
        language = self._detect_language(filename)
        
        # Collect all issues from the analysis pipeline
        all_issues = []
        
        # 1. Linting analysis
        try:
            if language == 'Python':
                lint_issues = self.linters['python'].lint(filename, code, changed_lines)
            elif language in ['JavaScript', 'TypeScript']:
                lint_issues = self.linters['js'].lint(filename, code, changed_lines)
            elif language == 'Go':
                lint_issues = self.linters['go'].lint(filename, code, changed_lines)
            elif language == 'Rust':
                lint_issues = self.linters['rust'].lint(filename, code, changed_lines)
            else:
                lint_issues = []
            
            all_issues.extend(lint_issues)
        except Exception as e:
            lint_issues = []

        # 2. Heuristic analysis
        try:
            heuristic_issues = []
            if language == 'Python' and 'python' in self.heuristics:
                heuristic_issues = self.heuristics['python'].analyze(filename, code, changed_lines)
            
            all_issues.extend(heuristic_issues)
        except Exception as e:
            pass

        # 3. LLM Analysis (Bug, Performance, Best Practices)
        try:
            # Bug analysis
            bug_issues = self.llm_agents['bug'].analyze(
                filename=filename,
                code=code,
                changed_lines=changed_lines,
                lint_issues=lint_issues,
                heuristic_issues=heuristic_issues
            )
            all_issues.extend(bug_issues)
            
            # Performance analysis  
            performance_issues = self.llm_agents['performance'].analyze(
                filename=filename,
                code=code,
                changed_lines=changed_lines,
                language=language,
                lint_issues=lint_issues,
                bug_issues=bug_issues
            )
            all_issues.extend(performance_issues)
            
            # Best practices analysis
            best_practices_issues = self.llm_agents['best_practices'].analyze(
                filename=filename,
                code=code,
                changed_lines=changed_lines,
                language=language,
                lint_issues=lint_issues,
                bug_issues=bug_issues,
                perf_issues=performance_issues
            )
            all_issues.extend(best_practices_issues)
            
        except Exception as e:
            pass
        
        # Post-process and deduplicate
        final_issues = deduplicate_issues(all_issues)
        
        return final_issues
    
    def _initialize_state(self, state: CodeReviewState) -> CodeReviewState:
        """Initialize the workflow state with PR data."""
        return {
            **state,
            'pr_metadata': self._extract_pr_metadata(),
            'files_data': self._extract_files_data(),
            'existing_context': self._extract_existing_context(),
            'current_file': None,
            'current_file_index': 0,
            'file_results': {},
            'analysis_context': {},
            'final_results': None,
            'error_message': None,
            'completed_files': []
        }
    
    def _start_file_processing(self, state: CodeReviewState) -> CodeReviewState:
        """Start processing the next file or indicate completion."""
        files_data = state.get('files_data', [])
        current_index = state.get('current_file_index', 0)
        
        if current_index < len(files_data):
            current_file = files_data[current_index]
            return {
                **state,
                'current_file': current_file,
                'analysis_context': {}  # Reset context for new file
            }
        
        # No more files to process
        return {
            **state,
            'current_file': None
        }
    
    def _should_continue_processing(self, state: CodeReviewState) -> str:
        """Decide whether to continue processing files or finish."""
        files_data = state.get('files_data', [])
        current_index = state.get('current_file_index', 0)
        

        
        if current_index < len(files_data):
            return 'process_file'
        return 'finish'
    
    def _lint_analysis(self, state: CodeReviewState) -> CodeReviewState:
        """Perform linting analysis on the current file."""
        current_file = state['current_file']
        if not current_file:
            return state
        
        filename = current_file['file_name']
        code = self._extract_code_from_patch(current_file.get('patch', ''))
        changed_lines = self._extract_changed_lines(current_file.get('patch', ''))
        language = self._detect_language(filename)
        
        # Run appropriate linter
        lint_issues = []
        if language == 'Python':
            lint_issues = self.linters['python'].lint(filename, code, changed_lines)
        elif language in ['JavaScript', 'TypeScript']:
            lint_issues = self.linters['js'].lint(filename, code, changed_lines)
        elif language == 'Go':
            lint_issues = self.linters['go'].lint(filename, code, changed_lines)
        elif language == 'Rust':
            lint_issues = self.linters['rust'].lint(filename, code, changed_lines)
        
        # Update analysis context
        analysis_context = state['analysis_context'].copy()
        analysis_context['lint_issues'] = lint_issues
        analysis_context['language'] = language
        analysis_context['code'] = code
        analysis_context['changed_lines'] = changed_lines
        analysis_context['filename'] = filename
        return {
            **state,
            'analysis_context': analysis_context
        }
    
    def _heuristic_analysis(self, state: CodeReviewState) -> CodeReviewState:
        """Perform heuristic-based analysis on the current file."""
        context = state['analysis_context']
        language = context.get('language', 'Unknown')
        
        heuristic_issues = []
        if language == 'Python' and 'python' in self.heuristics:
            heuristic_issues = self.heuristics['python'].analyze(
                context['filename'],
                context['code'],
                context['changed_lines']
            )
        
        # Update context
        context['heuristic_issues'] = heuristic_issues
        return {
            **state,
            'analysis_context': context
        }
    
    def _bug_analysis(self, state: CodeReviewState) -> CodeReviewState:
        """Perform LLM-based bug analysis."""
        context = state['analysis_context']
        
        bug_issues = self.llm_agents['bug'].analyze(
            filename=context['filename'],
            code=context['code'],
            changed_lines=context['changed_lines'],
            lint_issues=context.get('lint_issues', []),
            heuristic_issues=context.get('heuristic_issues', [])
        )
        
        context['bug_issues'] = bug_issues
        return {
            **state,
            'analysis_context': context
        }
    
    def _performance_analysis(self, state: CodeReviewState) -> CodeReviewState:
        """Perform LLM-based performance analysis."""
        context = state['analysis_context']
        
        performance_issues = self.llm_agents['performance'].analyze(
            filename=context['filename'],
            code=context['code'],
            changed_lines=context['changed_lines'],
            language=context.get('language', 'Unknown'),
            lint_issues=context.get('lint_issues', []),
            bug_issues=context.get('bug_issues', [])
        )
        
        context['performance_issues'] = performance_issues
        return {
            **state,
            'analysis_context': context
        }
    
    def _best_practices_analysis(self, state: CodeReviewState) -> CodeReviewState:
        """Perform LLM-based best practices analysis."""
        context = state['analysis_context']
        
        best_practices_issues = self.llm_agents['best_practices'].analyze(
            filename=context['filename'],
            code=context['code'],
            changed_lines=context['changed_lines'],
            language=context.get('language', 'Unknown'),
            lint_issues=context.get('lint_issues', []),
            bug_issues=context.get('bug_issues', []),
            perf_issues=context.get('performance_issues', [])
        )
        
        context['best_practices_issues'] = best_practices_issues
        return {
            **state,
            'analysis_context': context
        }
    
    def _finalize_file(self, state: CodeReviewState) -> CodeReviewState:
        """Finalize analysis for the current file and prepare for next."""
        context = state['analysis_context']
        filename = context['filename']
        
        # Collect all issues for this file
        all_issues = []
        all_issues.extend(context.get('lint_issues', []))
        all_issues.extend(context.get('heuristic_issues', []))
        all_issues.extend(context.get('bug_issues', []))
        all_issues.extend(context.get('performance_issues', []))
        all_issues.extend(context.get('best_practices_issues', []))
        
        # Post-process and deduplicate
        processed_issues = deduplicate_issues(all_issues)
        
        # Update state
        file_results = state['file_results'].copy()
        file_results[filename] = processed_issues
        
        completed_files = state['completed_files'].copy()
        completed_files.append(filename)
        return {
            **state,
            'file_results': file_results,
            'completed_files': completed_files,
            'current_file_index': state['current_file_index'] + 1
        }
    
    def _format_results(self, state: CodeReviewState) -> CodeReviewState:
        """Format the final results according to the expected schema."""
        file_reviews = []
        
        for filename, issues in state['file_results'].items():
            file_reviews.append({
                'name': filename,
                'issues': issues
            })
        
        # Calculate summary statistics
        total_issues = sum(len(f['issues']) for f in file_reviews)
        critical_issues = sum(
            1 for f in file_reviews 
            for issue in f['issues'] 
            if issue.get('type') == 'bug'
        )
        
        final_results = {
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
        return {
            **state,
            'final_results': final_results
        }
    
    def review(self) -> Dict[str, Any]:
        """
        Execute the LangGraph workflow to review the PR.
        
        Returns:
            Structured review results matching projectcontext.mdc format
        """
        try:
            # Execute the workflow with better error handling
            initial_state = CodeReviewState()
            final_state = self.workflow.invoke(
                initial_state,
            )
            
            result = final_state.get('final_results')
            if result is None:
                # Fallback if workflow didn't complete properly
                return {
                    'task_id': str(uuid.uuid4()),
                    'status': 'completed',
                    'results': {
                        'files': [],
                        'summary': {
                            'total_files': 0,
                            'total_issues': 0,
                            'critical_issues': 0
                        }
                    },
                    'message': 'Analysis completed with no results'
                }
            
            return result
            
        except Exception as e:
            raise
    
    # Helper methods (similar to BaseAgent)
    def _extract_pr_metadata(self) -> Dict[str, Any]:
        """Extract PR metadata from the final_payload."""
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
        """Extract file information from the final_payload."""
        return self.final_payload.get('file_info', [])
    
    def _extract_existing_context(self) -> Dict[str, Any]:
        """Extract existing reviews and comments from the final_payload."""
        return {
            'existing_reviews': self.final_payload.get('existing_reviews', []),
            'existing_comments': self.final_payload.get('existing_comments', [])
        }
    
    def _extract_changed_lines(self, patch: str) -> List[int]:
        """Extract line numbers that were changed from a GitHub patch."""
        if not patch:
            return []
        
        import re
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
                current_line += 1
                changed_lines.append(current_line)
            elif line.startswith('-') and not line.startswith('---'):
                pass
            elif not line.startswith('\\'):
                current_line += 1
        
        return sorted(list(set(changed_lines)))
    
    def _extract_code_from_patch(self, patch: str) -> str:
        """Extract the actual code content from a git patch."""
        if not patch:
            return ''
        
        code_lines = []
        
        for line in patch.split('\n'):
            if (line.startswith('@@') or 
                line.startswith('+++') or 
                line.startswith('---') or
                line.startswith('\\') or
                line.startswith('diff')):
                continue
            
            if line.startswith('+'):
                code_lines.append(line[1:])
            elif not line.startswith('-'):
                if line:
                    code_lines.append(line)
        
        return '\n'.join(code_lines)
    
    def _detect_language(self, filename: str) -> str:
        """Detect programming language from filename."""
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.jsx': 'JavaScript',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript',
            '.go': 'Go',
            '.rs': 'Rust',
        }
        
        for ext, lang in language_map.items():
            if filename.endswith(ext):
                return lang
        
        return 'Unknown' 
"""
Central LLM Service

Provides a unified interface for LLM interactions across different providers.
Supports structured prompts and responses for code review tasks.
Uses LangChain for standardized LLM interactions.
"""

import json
import os
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from dotenv import load_dotenv

# Load environment variables from parent directory
load_dotenv(dotenv_path="../.env")


class LLMProvider(Enum):
    """Supported LLM providers."""
    GEMINI = 'gemini'
    OPENAI = 'openai'
    ANTHROPIC = 'anthropic'


class LLMService:
    """
    Central service for LLM interactions.
    
    Provides a unified interface for different LLM providers with
    structured prompt handling and response parsing.
    """
    
    def __init__(self, provider: LLMProvider = LLMProvider.GEMINI,
                 api_key: Optional[str] = None):
        """
        Initialize the LLM service.
        
        Args:
            provider: The LLM provider to use
            api_key: API key for the provider (or use environment variable)
        """
        self.provider = provider
        self.api_key = api_key or self._get_api_key_from_env()
        self.client = self._initialize_client()
    
    def _get_api_key_from_env(self) -> Optional[str]:
        """Get API key from environment variables."""
        env_map = {
            LLMProvider.GEMINI: 'GOOGLE_API_KEY',  # Using your existing env var name
            LLMProvider.OPENAI: 'OPENAI_API_KEY', 
            LLMProvider.ANTHROPIC: 'ANTHROPIC_API_KEY'
        }
        return os.getenv(env_map.get(self.provider))
    
    def _initialize_client(self):
        """Initialize the appropriate LLM client."""
        if self.provider == LLMProvider.GEMINI:
            return self._initialize_gemini_client()
        elif self.provider == LLMProvider.OPENAI:
            return self._initialize_openai_client()
        else:
            raise NotImplementedError(
                f'Provider {self.provider.value} not implemented yet'
            )
    
    def _initialize_gemini_client(self):
        """Initialize Google Gemini client using LangChain."""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            # Check API key
            if not self.api_key:
                return None
            
            # Set GOOGLE_API_KEY for the client (required by Google's client)
            import os
            os.environ['GOOGLE_API_KEY'] = self.api_key
            
            return ChatGoogleGenerativeAI(
                model='gemini-2.0-flash-lite',
                google_api_key=self.api_key,
                temperature=0.1,
                max_tokens=1000
            )
            
        except ImportError as e:
            print(f'ImportError: langchain-google-genai not available: {e}')
            return None
        except Exception as e:
            print(f'ERROR: Failed to initialize Gemini client: {str(e)}')
            print(f'Error type: {type(e).__name__}')
            return None

    
    def _initialize_openai_client(self):
        """Initialize OpenAI client using LangChain."""
        try:
            from langchain_openai import ChatOpenAI
            
            return ChatOpenAI(
                model='gpt-3.5-turbo',
                openai_api_key=self.api_key,
                temperature=0.1,  # Low temperature for consistent code analysis
                max_tokens=1000
            )
        except ImportError:
            print('Warning: langchain-openai not installed. '
                  'Install with: pip install langchain-openai')
            print('Using mock responses.')
            return None
    
    def analyze_code_for_bugs(self, filename: str, code: str, 
                             changed_lines: List[int],
                             lint_issues: List[Dict[str, Any]] = None,
                             heuristic_issues: List[Dict[str, Any]] = None
                             ) -> List[Dict[str, Any]]:
        """
        Analyze code for potential bugs using LLM.
        
        Args:
            filename: Name of the file being analyzed
            code: Full code content or code fragment
            changed_lines: Lines that were changed in the PR
            lint_issues: Existing lint issues for context
            heuristic_issues: Issues found by static heuristics
            
        Returns:
            List of bug issues in standard format
        """
        prompt = self._build_bug_analysis_prompt(
            filename, code, changed_lines, lint_issues, heuristic_issues
        )
        
        response = self._send_prompt(prompt)
        return self._parse_bug_analysis_response(response)
    
    def _build_bug_analysis_prompt(self, filename: str, code: str,
                                  changed_lines: List[int],
                                  lint_issues: List[Dict[str, Any]] = None,
                                  heuristic_issues: List[Dict[str, Any]] = None
                                  ) -> str:
        """Build a focused prompt for bug analysis."""
        
        prompt = f"""You are an expert code reviewer specializing in bug detection.
Your task is to analyze the provided code and identify potential BUGS and LOGIC ERRORS only.

**IMPORTANT GUIDELINES:**
- Focus ONLY on potential runtime errors, logic bugs, and correctness issues
- IGNORE style, formatting, performance, or best practice issues
- Be specific about WHY something could be a bug
- Provide actionable suggestions to fix the issues
- Only flag issues on the changed lines: {changed_lines}

**File:** {filename}

**Code to analyze:**
```
{code}
```

**Changed lines:** {', '.join(map(str, changed_lines))}
"""

        # Add context from existing analysis
        if lint_issues:
            prompt += f"""
**Existing lint issues for context:**
{self._format_existing_issues(lint_issues)}
"""

        if heuristic_issues:
            prompt += f"""
**Static heuristic findings:**
{self._format_existing_issues(heuristic_issues)}
"""

        prompt += """
**Please respond with a JSON array of bug issues. Each issue should have:**
- "line": line number where the issue occurs
- "description": clear explanation of the potential bug
- "suggestion": specific fix recommendation
- "confidence": your confidence level (high/medium/low)

**Example response format:**
```json
[
    {
        "line": 15,
        "description": "Potential null pointer exception: variable 'user' may be null when accessing 'user.name'",
        "suggestion": "Add null check: if user is not None before accessing user.name",
        "confidence": "high"
    }
]
```

If no bugs are found, return an empty array: []
"""
        return prompt
    
    def _format_existing_issues(self, issues: List[Dict[str, Any]]) -> str:
        """Format existing issues for context in prompts."""
        if not issues:
            return 'None'
        
        formatted = []
        for issue in issues:
            formatted.append(
                f"- Line {issue.get('line', '?')}: {issue.get('description', 'Unknown issue')}"
            )
        return '\n'.join(formatted)
    
    def _send_prompt(self, prompt: str) -> str:
        """Send prompt to the LLM and return response using LangChain."""
        if not self.client:
            return self._mock_response()
        
        try:
            from langchain_core.messages import HumanMessage
            
            # LangChain uses a unified interface for all providers
            messages = [HumanMessage(content=prompt)]
            response = self.client.invoke(messages)
            
            # Extract content from the response
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
                
        except Exception as e:
            print(f'Error calling LLM via LangChain: {e}')
            return self._mock_response()
    
    def _mock_response(self) -> str:
        """Return a mock response when LLM is not available."""
        return '[]'  # Empty JSON array indicating no issues found
    
    def _parse_bug_analysis_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into standard issue format."""
        try:
            # Extract JSON from response (in case there's extra text)
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                return []
            
            json_str = response[json_start:json_end]
            llm_issues = json.loads(json_str)
            
            # Convert to standard format
            standard_issues = []
            for issue in llm_issues:
                if isinstance(issue, dict):
                    standard_issues.append({
                        'type': 'bug',
                        'line': issue.get('line', 0),
                        'description': issue.get('description', 'LLM-detected bug'),
                        'suggestion': issue.get('suggestion', 'Review this code for potential issues')
                    })
            
            return standard_issues
            
        except (json.JSONDecodeError, Exception) as e:
            print(f'Error parsing LLM response: {e}')
            return []
    
    def generate_custom_analysis(self, prompt: str) -> str:
        """
        Send a custom prompt to the LLM for general analysis.
        
        Args:
            prompt: Custom prompt string
            
        Returns:
            Raw LLM response
        """
        return self._send_prompt(prompt) 

    def analyze_code_for_performance(self, filename: str, code: str, 
                                   changed_lines: List[int], 
                                   language: str = 'Unknown',
                                   lint_issues: List[Dict[str, Any]] = None,
                                   bug_issues: List[Dict[str, Any]] = None
                                   ) -> List[Dict[str, Any]]:
        """
        Analyze code for potential performance issues using LLM.
        
        Args:
            filename: Name of the file being analyzed
            code: Full code content or code fragment
            changed_lines: Lines that were changed in the PR
            language: Programming language for context
            lint_issues: Existing lint issues for context
            bug_issues: Issues found by bug analysis for context
            
        Returns:
            List of performance issues in standard format
        """
        prompt = self._build_performance_analysis_prompt(
            filename, code, changed_lines, language, lint_issues, bug_issues
        )
        
        response = self._send_prompt(prompt)
        return self._parse_performance_analysis_response(response)

    def _build_performance_analysis_prompt(self, filename: str, code: str,
                                         changed_lines: List[int], 
                                         language: str = 'Unknown',
                                         lint_issues: List[Dict[str, Any]] = None,
                                         bug_issues: List[Dict[str, Any]] = None
                                         ) -> str:
        """Build a focused prompt for performance analysis."""
        
        prompt = f"""You are an expert code reviewer specializing in 
performance optimization. Your task is to analyze the provided code and 
identify potential PERFORMANCE ISSUES and OPTIMIZATION OPPORTUNITIES only.

**IMPORTANT GUIDELINES:**
- Focus ONLY on performance-related issues (efficiency, optimization)
- IGNORE bugs, style, formatting, or general best practices
- Look for: unnecessary loops, inefficient algorithms, repeated computations,
  poor data structures, N+1 queries, lack of caching, excessive I/O
- Be specific about WHY something affects performance
- Provide actionable optimization suggestions
- Only flag issues on the changed lines: {changed_lines}
- Consider the programming language context: {language}

**File:** {filename}
**Language:** {language}

**Code to analyze:**
```
{code}
```

**Changed lines:** {', '.join(map(str, changed_lines))}
"""

        # Add context from existing analysis
        if lint_issues:
            prompt += f"""
**Existing lint issues for context:**
{self._format_existing_issues(lint_issues)}
"""

        if bug_issues:
            prompt += f"""
**Bug analysis findings for context:**
{self._format_existing_issues(bug_issues)}
"""

        prompt += """
**Please respond with a JSON array of performance issues. Each issue should have:**
- "line": line number where the issue occurs
- "description": clear explanation of the performance concern
- "suggestion": specific optimization recommendation
- "impact": estimated performance impact (high/medium/low)

**Example response format:**
```json
[
    {
        "line": 25,
        "description": "Nested loop creates O(n²) complexity for simple lookup operation",
        "suggestion": "Use a hash set for O(1) lookup: lookup_set = set(items)",
        "impact": "high"
    }
]
```

If no performance issues are found, return an empty array: []
"""
        return prompt

    def _parse_performance_analysis_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into standard performance issue format."""
        try:
            # Extract JSON from response (in case there's extra text)
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                return []
            
            json_str = response[json_start:json_end]
            llm_issues = json.loads(json_str)
            
            # Convert to standard format
            standard_issues = []
            for issue in llm_issues:
                if isinstance(issue, dict):
                    standard_issues.append({
                        'type': 'performance',
                        'line': issue.get('line', 0),
                        'description': issue.get('description', 'LLM-detected performance issue'),
                        'suggestion': issue.get('suggestion', 'Review this code for optimization opportunities')
                    })
            
            return standard_issues
            
        except (json.JSONDecodeError, Exception) as e:
            print(f'Error parsing performance analysis response: {e}')
            return []

    def analyze_code_for_best_practices(self, filename: str, code: str, 
                                      changed_lines: List[int], 
                                      language: str = 'Unknown',
                                      lint_issues: List[Dict[str, Any]] = None,
                                      bug_issues: List[Dict[str, Any]] = None,
                                      perf_issues: List[Dict[str, Any]] = None
                                      ) -> List[Dict[str, Any]]:
        """
        Analyze code for best practices adherence using LLM.
        
        Args:
            filename: Name of the file being analyzed
            code: Full code content or code fragment
            changed_lines: Lines that were changed in the PR
            language: Programming language for context
            lint_issues: Existing lint issues for context
            bug_issues: Issues found by bug analysis for context
            perf_issues: Issues found by performance analysis for context
            
        Returns:
            List of best practices issues in standard format
        """
        prompt = self._build_best_practices_analysis_prompt(
            filename, code, changed_lines, language, 
            lint_issues, bug_issues, perf_issues
        )
        
        response = self._send_prompt(prompt)
        return self._parse_best_practices_analysis_response(response)

    def _build_best_practices_analysis_prompt(self, filename: str, code: str,
                                            changed_lines: List[int], 
                                            language: str = 'Unknown',
                                            lint_issues: List[Dict[str, Any]] = None,
                                            bug_issues: List[Dict[str, Any]] = None,
                                            perf_issues: List[Dict[str, Any]] = None
                                            ) -> str:
        """Build a focused prompt for best practices analysis."""
        
        prompt = f"""You are an expert code reviewer specializing in 
best practices, maintainability, and code quality. Your task is to analyze 
the provided code and identify opportunities for improving MAINTAINABILITY, 
READABILITY, and adherence to IDIOMATIC DEVELOPMENT STANDARDS only.

**IMPORTANT GUIDELINES:**
- Focus ONLY on best practices, maintainability, and readability issues
- IGNORE bugs, performance issues, and style/formatting (already covered)
- Look for: unclear naming, overly complex functions, lack of modularity,
  poor separation of concerns, missing documentation, hard-to-test code,
  violation of language idioms, over-engineering, tight coupling
- Be specific about WHY something affects maintainability/readability
- Provide actionable refactoring suggestions
- Only flag issues on the changed lines: {changed_lines}
- Consider the programming language context: {language}

**File:** {filename}
**Language:** {language}

**Code to analyze:**
```
{code}
```

**Changed lines:** {', '.join(map(str, changed_lines))}
"""

        # Add context from existing analysis to avoid duplication
        if lint_issues:
            prompt += f"""
**Existing lint issues (DO NOT REPEAT):**
{self._format_existing_issues(lint_issues)}
"""

        if bug_issues:
            prompt += f"""
**Bug analysis findings (DO NOT REPEAT):**
{self._format_existing_issues(bug_issues)}
"""

        if perf_issues:
            prompt += f"""
**Performance analysis findings (DO NOT REPEAT):**
{self._format_existing_issues(perf_issues)}
"""

        prompt += """
**Please respond with a JSON array of best practices issues. Each issue should have:**
- "line": line number where the issue occurs
- "description": clear explanation of the maintainability/readability concern
- "suggestion": specific refactoring or improvement recommendation
- "category": type of best practice (readability/maintainability/idiom/testing)

**Example response format:**
```json
[
    {
        "line": 42,
        "description": "Function 'process_data' is too long (25 lines) and handles multiple concerns",
        "suggestion": "Break into smaller functions: separate validation, processing, and formatting logic",
        "category": "maintainability"
    }
]
```

If no best practices issues are found, return an empty array: []
"""
        return prompt

    def _parse_best_practices_analysis_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into standard best practices issue format."""
        try:
            # Extract JSON from response (in case there's extra text)
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                return []
            
            json_str = response[json_start:json_end]
            llm_issues = json.loads(json_str)
            
            # Convert to standard format
            standard_issues = []
            for issue in llm_issues:
                if isinstance(issue, dict):
                    standard_issues.append({
                        'type': 'best_practice',
                        'line': issue.get('line', 0),
                        'description': issue.get('description', 'LLM-detected best practice issue'),
                        'suggestion': issue.get('suggestion', 'Review code for maintainability improvements')
                    })
            
            return standard_issues
            
        except (json.JSONDecodeError, Exception) as e:
            print(f'Error parsing best practices analysis response: {e}')
            return [] 
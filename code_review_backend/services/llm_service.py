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
            LLMProvider.GEMINI: 'GEMINI_API_KEY',  # Using your existing env var name
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
            
            # LangChain will automatically use GOOGLE_API_KEY from environment
            return ChatGoogleGenerativeAI(
                model='gemini-1.5-flash',  # Updated model name
                google_api_key=self.api_key,
                temperature=0.1,  # Low temperature for consistent code analysis
                max_tokens=1000
            )
        except ImportError:
            print('Warning: langchain-google-genai not installed. '
                  'Install with: pip install langchain-google-genai')
            print('Using mock responses.')
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
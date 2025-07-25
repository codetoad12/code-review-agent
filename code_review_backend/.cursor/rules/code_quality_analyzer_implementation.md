# Code Quality Analyzer Implementation

## Overview

This module handles code quality analysis using language-specific linters. It supports:

- Python (ruff)
- Go (golangci-lint)
- Rust (clippy)
- JavaScript/TypeScript (eslint)

If a linter is not available for a language, the system falls back to an LLM-based analyzer.
We are using langchain/langgraph and gemini as the llm backend stac.
---

## Directory Structure

```bash
agents/
├── analyzers/
│   ├── code_quality.py         # Dispatcher
│   └── linters/
│       ├── python_linter.py    # Ruff
│       ├── go_linter.py        # golangci-lint
│       ├── rust_linter.py      # Clippy
│       └── js_linter.py        # ESLint
```

---

## Dispatcher Logic (`code_quality.py`)

```python
class CodeQualityAnalyzer:
    def analyze(self, language, filename, patch, raw_code, changed_lines):
        if language == "Python":
            return run_python_linter(filename, raw_code, changed_lines)
        elif language == "Go":
            return run_golangci_lint(filename, raw_code, changed_lines)
        elif language == "Rust":
            return run_clippy(filename, raw_code, changed_lines)
        elif language in ["JavaScript", "TypeScript"]:
            return run_eslint(filename, raw_code, changed_lines)
        else:
            return self._analyze_with_llm(filename, patch)
```

---

## Linter Tools

| Language     | Tool            | CLI Command                                 |
|--------------|------------------|----------------------------------------------|
| Python       | Ruff             | `ruff <file> --format json`                 |
| Go           | golangci-lint    | `golangci-lint run <file> --out-format json`|
| Rust         | Clippy           | `cargo clippy` (requires cargo project)     |
| JavaScript   | ESLint           | `eslint <file> -f json`                     |

---

## LLM Fallback

```python
def _analyze_with_llm(self, filename, patch):
    prompt = f"""You are reviewing a file named {filename}. Identify style issues in this diff:
{patch}

Return JSON like:
[
  {{
    "type": "style",
    "line": 42,
    "description": "...",
    "suggestion": "..."
  }}
]
"""
    return eval(call_llm_with_prompt(prompt))
```

---

## Instructions on how to proceed:
Do not build all the linters at once.
Build it one at a time. 
Before building each linter give a detailed plan on how it is going to be built. Allow the user to review the plan and give approval before proceed.


## Additional implementation details

- Implement each linter module with subprocess calls
- Normalize output to standard issue format
- Add test cases for each linter
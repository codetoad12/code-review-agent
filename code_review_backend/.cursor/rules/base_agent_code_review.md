# BaseAgent Implementation for Code Review

## Overview

The `BaseAgent` class acts as the orchestrator for code analysis. It accepts pre-parsed GitHub PR input and runs one or more analyzers (e.g., code quality, bug detection, performance) over each file.

This version includes integration with the `CodeQualityAnalyzer`, which uses language-specific linters or falls back to LLM-based review.

---

## Directory Context

```bash
agents/
├── base_agent.py
├── analyzers/
│   └── code_quality.py
```

---

## Responsibilities

- Accept PR metadata (output from format_pr_data_to_pass_to_agent in handlers/pr_handlers.py) (title, description, language)
- Segregate that data into the respective keys present in the metadata passed above.

---
## Usage Example

```python
from agents.base_agent import BaseAgent
from agents.analyzers.code_quality import CodeQualityAnalyzer

agent = BaseAgent(analyzers=[CodeQualityAnalyzer()])
output = agent.review(pr_metadata, file_list)
```

---

## Next Steps

- Add bug/performance/best_practices analyzers
- Integrate into Celery tasks
- Include caching and logging
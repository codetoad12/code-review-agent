# Code Review Agent Backend

An autonomous code review agent system that uses AI to analyze GitHub pull requests. The system implements a goal-oriented AI agent that can plan and execute code reviews independently and provides structured feedback through a REST API.

## Features

- 🔍 **Multi-language Support**: Python, JavaScript, TypeScript, Go, Rust
- 🚀 **Synchronous Processing**: Direct API responses (Celery integration planned)
- 🛠️ **Smart Linting**: Language-specific linters with LLM fallback
- 📝 **Migration Filtering**: Automatically skips migration files
- 🔗 **GitHub Integration**: Fetches PR data, files, comments, and reviews
- 📊 **Structured Output**: Standardized issue reporting format

## Tech Stack

- **Backend**: FastAPI (Python)
- **Linting Tools**: 
  - Python: Ruff
  - JavaScript/TypeScript: ESLint
  - Go: golangci-lint (planned)
  - Rust: clippy (planned)
- **GitHub API**: httpx client
- **AI/LLM**: Planned integration with Langchain + Gemini

## Project Structure

```
code_review_backend/
├── agents/
│   ├── base_agent.py           # Main orchestrator
│   └── analyzers/
│       ├── code_quality.py     # Language dispatcher
│       └── linters/
│           ├── python_linter.py    # Ruff integration
│           └── js_linter.py        # ESLint integration (planned)
├── handlers/
│   └── pr_handlers.py          # GitHub API integration
├── routes/
│   └── pr.py                   # API endpoints
├── main.py                     # FastAPI application
├── package.json                # Node.js dependencies
└── README.md                   # This file
```

## Setup Instructions

### 1. Python Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install fastapi httpx pydantic uvicorn ruff
```

### 2. Node.js Dependencies (for JavaScript linting)

```bash
# Install Node.js dependencies
npm install

# Verify ESLint installation
npx eslint --version
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```bash
# GitHub API token (optional but recommended for higher rate limits)
GITHUB_TOKEN=your_github_token_here
```

### 4. Run the Application

```bash
# Start the FastAPI development server
uvicorn main:app --reload --port 8000

# The API will be available at http://localhost:8000
# API documentation at http://localhost:8000/docs
```

## API Endpoints

### Analyze Pull Request

**POST** `/analyze_pr`

Analyzes a GitHub pull request and returns code review results.

**Request Body:**
```json
{
  "repo_owner": "username",
  "repo_name": "repository",
  "pr_number": 123
}
```

**Response:**
```json
{
  "message": "PR analysis completed",
  "status": "completed",
  "results": {
    "task_id": "uuid",
    "status": "completed",
    "results": {
      "files": [
        {
          "name": "src/example.py",
          "issues": [
            {
              "type": "style",
              "line": 42,
              "description": "Line too long (85 > 79 characters)",
              "suggestion": "Break line into multiple lines"
            }
          ]
        }
      ],
      "summary": {
        "total_files": 1,
        "total_issues": 1,
        "critical_issues": 0
      }
    }
  }
}
```

## Supported Languages

| Language       | Linter         | Status      |
|----------------|----------------|-------------|
| Python         | Ruff           | ✅ Implemented |
| JavaScript     | ESLint         | 🚧 In Progress |
| TypeScript     | ESLint         | 🚧 In Progress |
| Go             | golangci-lint  | 📋 Planned |
| Rust           | clippy         | 📋 Planned |

## Development

### Running Tests

```bash
# Python tests (when implemented)
pytest

# JavaScript linting test
npm run lint:js
```

### Adding New Linters

1. Create a new linter class in `agents/analyzers/linters/`
2. Implement the standard interface: `lint(filename, raw_code, changed_lines)`
3. Update the language mapping in `code_quality.py`
4. Add language detection patterns

### Migration File Filtering

The system automatically excludes common migration file patterns:

- Django: `**/migrations/*.py`
- Rails: `db/migrate/*.rb`
- Laravel: `database/migrations/*.php`
- Node.js: `**/migrations/*.{js,ts}`
- Alembic: `alembic/versions/*.py`

## Future Enhancements

- [ ] Celery + Redis integration for async processing
- [ ] LLM-based analysis for unsupported languages
- [ ] Advanced GitHub integration (posting review comments)
- [ ] Configuration file support for custom linting rules
- [ ] Performance metrics and caching
- [ ] Docker containerization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details. 
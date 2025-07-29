# Code Review Agent

An autonomous AI-powered code review agent that analyzes GitHub pull requests asynchronously using Celery and Redis.

## 🚀 **NEW: LangGraph-Based Architecture**

This project now uses **LangGraph** for sophisticated workflow orchestration, providing:
- **Stateful Graph Workflows**: Complex analysis pipelines with state management
- **Better Agent Collaboration**: Seamless integration between different analyzers
- **Cyclic Processing**: Support for iterative analysis and feedback loops
- **Advanced Orchestration**: Graph-based execution with conditional logic
- **Built-in Memory**: Persistent state across analysis steps

## Features

- **Asynchronous Processing**: Uses Celery for background task processing
- **Multi-language Support**: Python, JavaScript, TypeScript, Go, Rust
- **AI-Powered Analysis**: Detects bugs, performance issues, and style problems
- **Task Tracking**: Monitor analysis progress with task IDs
- **Docker Support**: Complete containerized deployment
- **RESTful API**: Clean API endpoints for integration
- **LangGraph Workflows**: Sophisticated multi-agent orchestration

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   FastAPI   │───▶│    Redis    │◀───│   Celery    │
│   Server    │    │   Message   │    │   Worker    │
│             │    │   Broker    │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
       │                                      │
       └──────────────────┐                  │
                          ▼                  ▼
                   ┌─────────────────────────────┐
                   │     LangGraph Agent         │
                   │  ╭─────────────────────╮    │
                   │  │ 1. Lint Analysis    │    │
                   │  │ 2. Heuristic Check  │    │
                   │  │ 3. Bug Detection    │    │
                   │  │ 4. Performance      │    │
                   │  │ 5. Best Practices   │    │
                   │  ╰─────────────────────╯    │
                   └─────────────────────────────┘
```

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone and navigate to the project:**
```bash
cd code_review_backend
```

2. **Start all services:**
```bash
docker-compose up --build
```

This will start:
- FastAPI server on `http://localhost:8000`
- Redis on `localhost:6379`
- Celery worker for processing tasks

### Manual Setup

1. **Install Redis:**
```bash
# On macOS
brew install redis
redis-server

# On Ubuntu
sudo apt install redis-server
sudo systemctl start redis
```

2. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

3. **Start the services:**

Terminal 1 - FastAPI server:
```bash
cd code_review_backend
uvicorn main:app --reload --port 8000
```

Terminal 2 - Celery worker:
```bash
cd code_review_backend
celery -A celery_app worker --loglevel=info
```

## API Endpoints

### 1. Start PR Analysis

**POST** `/api/v1/analyze-pr`

Start asynchronous analysis of a GitHub pull request.

**Request:**
```json
{
  "repo_owner": "facebook",
  "repo_name": "react",
  "pr_number": 12345
}
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "PR analysis started",
  "status": "pending"
}
```

### 2. Check Task Status

**GET** `/api/v1/status/{task_id}`

Check the current status of an analysis task.

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Analyzing code with AI agents..."
}
```

Possible statuses:
- `pending`: Task is queued
- `processing`: Task is being executed
- `completed`: Task finished successfully
- `failed`: Task encountered an error

### 3. Get Results

**GET** `/api/v1/results/{task_id}`

Retrieve the analysis results for a completed task.

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "results": {
    "files": [
      {
        "name": "src/components/Button.tsx",
        "issues": [
          {
            "type": "style",
            "line": 42,
            "description": "Line too long (85 > 79 characters)",
            "suggestion": "Break line into multiple lines"
          },
          {
            "type": "bug",
            "line": 23,
            "description": "Potential null pointer exception",
            "suggestion": "Add null check before accessing property"
          }
        ]
      }
    ],
    "summary": {
      "total_files": 1,
      "total_issues": 2,
      "critical_issues": 1
    }
  },
  "message": "Analysis completed successfully"
}
```

## Example Usage

```bash
# 1. Start analysis
curl -X POST "http://localhost:8000/api/v1/analyze-pr" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_owner": "facebook",
    "repo_name": "react", 
    "pr_number": 12345
  }'

# Response: {"task_id": "abc123...", "status": "pending"}

# 2. Check status
curl "http://localhost:8000/api/v1/status/abc123..."

# 3. Get results (when completed)
curl "http://localhost:8000/api/v1/results/abc123..."
```

## Configuration

### Environment Variables

Create a `.env` file:

```env
# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# GitHub API (optional, for higher rate limits)
GITHUB_TOKEN=your_github_token_here

# LLM Configuration (choose one)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
```

### Celery Configuration

The Celery worker can be customized:

```bash
# Run with specific concurrency
celery -A celery_app worker --loglevel=info --concurrency=4

# Run specific queues
celery -A celery_app worker --loglevel=info --queues=analysis

# Monitor tasks
celery -A celery_app flower
```

## Supported Languages

| Language   | Linter        | AI Analysis | Status |
|------------|---------------|-------------|---------|
| Python     | Ruff          | ✅          | ✅      |
| JavaScript | ESLint        | ✅          | 🚧      |
| TypeScript | ESLint        | ✅          | 🚧      |
| Go         | golangci-lint | ✅          | 📋      |
| Rust       | clippy        | ✅          | 📋      |

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Adding New Analyzers

1. Create analyzer in `agents/analyzers/`
2. Register in `agents/analyzers/pipeline.py`
3. Add configuration in `celery_app.py`

### Monitoring

- **Health Check**: `GET /health`
- **API Docs**: `http://localhost:8000/docs`
- **Redis Monitoring**: Use Redis CLI or GUI tools
- **Celery Monitoring**: Install Flower for web-based monitoring

## Deployment

### Production Docker Setup

```yaml
version: '3.8'
services:
  web:
    image: your-registry/code-review-agent:latest
    ports:
      - "80:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - GITHUB_TOKEN=${GITHUB_TOKEN}
    depends_on:
      - redis

  worker:
    image: your-registry/code-review-agent:latest
    command: celery -A celery_app worker --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

  redis:
    image: redis:latest
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - see LICENSE file for details. 
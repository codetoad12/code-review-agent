# Environment Setup Guide

## Issue Resolution: Environment Keys Not Found in Docker

The Docker containers were missing the required API keys for LLM services. This has been fixed by updating the `docker-compose.yml` file.

## Required Environment Variables

The application requires the following environment variables:

### 1. Create a `.env` file in the project root

Create a `.env` file in the same directory as `docker-compose.yml` with the following content:

```bash
# Redis Configuration
REDIS_URL=redis://redis:6379/0

# LLM API Keys (replace with your actual keys)
GOOGLE_API_KEY=your_google_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Set default LLM provider
DEFAULT_LLM_PROVIDER=gemini
```

### 2. Get API Keys

- **Google API Key (Gemini)**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
- **Anthropic API Key**: Get from [Anthropic Console](https://console.anthropic.com/)

### 3. Alternative: Set Environment Variables Directly

If you prefer not to use a `.env` file, you can set the environment variables in your shell:

#### Windows (PowerShell)
```powershell
$env:GOOGLE_API_KEY="your_api_key_here"
$env:OPENAI_API_KEY="your_api_key_here"
$env:ANTHROPIC_API_KEY="your_api_key_here"
```

#### Linux/macOS (Bash)
```bash
export GOOGLE_API_KEY="your_api_key_here"
export OPENAI_API_KEY="your_api_key_here"
export ANTHROPIC_API_KEY="your_api_key_here"
```

## Running the Application

After setting up the environment variables:

```bash
docker-compose up --build
```

## Verification

The application will now properly load the API keys and you should see logs indicating successful initialization of the LLM services.

## Security Note

- Never commit your `.env` file to version control
- Add `.env` to your `.gitignore` file
- Use environment-specific configurations for production deployments 
FROM python:3.11

WORKDIR /app

# Copy only the subfolder (to keep context small)
COPY code_review_backend/ /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Adjust entrypoint if your app file is inside this folder
CMD ["uvicorn", "code_review_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

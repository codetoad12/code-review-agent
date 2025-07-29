FROM python:3.11

WORKDIR /app

# Copy the entire repo (including code_review_backend and requirements.txt)
COPY . /app

# Install dependencies from inside the subfolder
RUN pip install --no-cache-dir -r code_review_backend/requirements.txt

# Optional: create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Run FastAPI from the full module path
CMD ["uvicorn", "code_review_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-slim
WORKDIR /app

# Install Poetry
RUN pip install --upgrade pip
RUN pip install poetry

# Copy all source code
COPY . .

# Prevent Poetry from creating a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-root


# Use uvicorn to run the FastAPI app
CMD ["poetry", "run", "uvicorn", "src.instaserver:app", "--host", "0.0.0.0", "--port", "8000"]

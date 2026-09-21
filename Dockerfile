FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONBUFFERED=1 UV_COMPILE_BYTECODE=1

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

COPY README.md ./
COPY src/ src/
RUN uv sync --no-dev

COPY artifact/ artifact/

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "grade_perform.service.app:app", "--host", "0.0.0.0", "--port", "8000"]
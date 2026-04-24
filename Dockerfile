FROM python:3.14-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --system

COPY src/ src/

EXPOSE 8000

CMD ["uvicorn", "ivanpashkulev.main:app", "--host", "0.0.0.0", "--port", "8000"]

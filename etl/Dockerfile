FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

COPY pyproject.toml ./
COPY src ./src
COPY services ./services
COPY SQL ./SQL
COPY data ./data
COPY tests ./tests

CMD ["python", "-m", "src.main"]

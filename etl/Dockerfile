FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt requirements-dev.txt constraints.txt ./
RUN pip install -c constraints.txt -r requirements.txt

COPY pyproject.toml ./
COPY src ./src
COPY services ./services
COPY SQL ./SQL
COPY data ./data

FROM base AS test
RUN pip install -c constraints.txt -r requirements-dev.txt
COPY tests ./tests
CMD ["pytest", "-ra"]

FROM base AS runtime
RUN useradd --create-home --uid 10001 etl
USER etl

CMD ["python", "-m", "src.main"]

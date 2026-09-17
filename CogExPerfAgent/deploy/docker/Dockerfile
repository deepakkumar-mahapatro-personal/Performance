FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app

RUN groupadd --gid 10001 perfagent \
    && useradd \
        --uid 10001 \
        --gid 10001 \
        --create-home \
        --shell /usr/sbin/nologin \
        perfagent

COPY requirements.txt .

RUN python -m pip install --no-cache-dir \
    -r requirements.txt

COPY app ./app
COPY config ./config

RUN mkdir -p \
        /tmp/perf-agent \
        /tmp/matplotlib \
    && chown -R 10001:10001 \
        /app \
        /tmp/perf-agent \
        /tmp/matplotlib

USER 10001:10001

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8080"]
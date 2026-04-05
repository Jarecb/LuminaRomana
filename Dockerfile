FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LUMINA_ROMANA_ENV=production
ENV LUMINA_ROMANA_DATA_DIR=/app/data
ENV LUMINA_ROMANA_WEB_HOST=0.0.0.0
ENV LUMINA_ROMANA_WEB_PORT=8000

WORKDIR /app

COPY pyproject.toml README.md main.py ./
COPY app ./app

RUN python -m pip install --upgrade pip \
    && pip install .

EXPOSE 8000

CMD ["python", "main.py", "serve"]

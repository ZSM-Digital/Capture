FROM mcr.microsoft.com/playwright/python:v1.51.0-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY capture /app/capture

RUN mkdir -p /var/lib/capture/assets \
 && chown -R pwuser:pwuser /app /var/lib/capture/assets
USER pwuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"

CMD ["python", "-m", "uvicorn", "capture.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

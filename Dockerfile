# ---- build stage ----
FROM python:3.12-slim AS builder
WORKDIR /build
COPY app/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- runtime stage (small, non-root) ----
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=5000
RUN groupadd -r app && useradd -r -g app -u 10001 app
WORKDIR /srv
COPY --from=builder /install /usr/local
COPY app/ /srv/
RUN mkdir -p /data && chown app:app /data
USER 10001
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request as u;u.urlopen('http://127.0.0.1:5000/healthz')" || exit 1
CMD ["gunicorn","-b","0.0.0.0:5000","-w","2","--preload","--access-logfile","-","app:app"]

# Stage 1: Build dependencies
FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    gcc pkg-config default-libmysqlclient-dev && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    default-libmysqlclient-dev && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate && python manage.py init_admin && gunicorn k8s_console.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120"]

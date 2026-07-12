# Stage 1: Build dependencies
FROM python:{PYTHON_VERSION}-slim AS builder
WORKDIR /app
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    gcc pkg-config default-libmysqlclient-dev && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:{PYTHON_VERSION}-slim
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    default-libmysqlclient-dev && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY . .
RUN if [ -f start_app.sh ]; then chmod +x start_app.sh; fi
RUN mkdir -p /data/project/{APP_NAME}/logs
EXPOSE 8000
CMD ["sh", "-c", "./start_app.sh"]

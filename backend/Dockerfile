
FROM python:3.13-slim

# --------------------------------------------------
# Environment
# --------------------------------------------------

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Temporary workaround for Azure MCP/.NET
# Sprint 3 will move Azure MCP into a dedicated container

# --------------------------------------------------
# System Dependencies
# --------------------------------------------------

RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    ca-certificates \
    git \
    build-essential \
    libicu-dev \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------
# Install NodeJS
# --------------------------------------------------

RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash -

RUN apt-get update && apt-get install -y \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------
# Verify Node Installation
# --------------------------------------------------

RUN node --version
RUN npm --version

# --------------------------------------------------
# Install Python Dependencies
# --------------------------------------------------

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_DEFAULT_TIMEOUT=120

RUN pip install --no-cache-dir --retries 10 --timeout 120 --prefer-binary -r requirements.txt

# --------------------------------------------------
# Copy Application
# --------------------------------------------------

COPY . .

# --------------------------------------------------
# Expose FastAPI
# --------------------------------------------------

EXPOSE 8000

# --------------------------------------------------
# Start FastAPI
# --

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]

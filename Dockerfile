# ─────────────────────────────────────────────────────────────
# Dockerfile — Geldium AI Collections System
# ─────────────────────────────────────────────────────────────
# What this file does, line by line:
#
# 1. Start from an official Python image (slim = no bloat)
# 2. Set the working directory inside the container
# 3. Copy requirements.txt in FIRST (Docker caches this layer —
#    if requirements don't change, it won't reinstall packages
#    on every rebuild. Saves time.)
# 4. Install all Python packages
# 5. Copy ALL your code in
# 6. Tell Docker what port the app uses
# 7. Default command to run when container starts
#
# WHY python:3.11-slim?
#   - 3.11 is stable and fast
#   - slim = minimal Ubuntu base, no extra OS tools
#   - smaller image = faster to build, deploy, and run
# ─────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Set working directory inside the container
# All subsequent commands run from here
# Think of it as: cd /app inside the container
WORKDIR /app

# Install system dependencies first
# These are OS-level packages some Python libs need to compile
# --no-install-recommends = don't install optional extras (keeps image lean)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (before code)
# Why? Docker builds in layers. If requirements.txt hasn't changed,
# Docker uses its cached layer and skips reinstalling packages.
# This makes rebuilds after code changes MUCH faster.
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir = don't store pip's download cache inside the image
#                  keeps image size smaller
RUN pip install --no-cache-dir -r requirements.txt

# Now copy all your project files into the container
# The . . means: copy everything from your local folder → /app in container
# This comes AFTER pip install so code changes don't bust the pip cache
COPY . .

# Create the logs directory inside the container
# The agent writes audit logs here at runtime
RUN mkdir -p logs

# Tell Docker this container listens on port 8000
# This is documentation — doesn't actually open the port
# Port mapping happens in docker-compose.yml
EXPOSE 8000

# Default command — what runs when this container starts
# Can be overridden in docker-compose.yml (scheduler uses a different command)
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

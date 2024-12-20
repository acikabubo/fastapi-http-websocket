FROM python:3.13.0-slim-bullseye
# FROM ghcr.io/astral-sh/uv:python3.13-alpine

LABEL maintainer="Aleksandar Krsteski <aleksandar.krsteski@ved.mk>"
LABEL description="HTTP & WebSocket Handlers"

# General system staff
RUN apt update
RUN apt-get upgrade -y && apt autoremove -y
RUN apt install -my \
    bash \
    build-essential \
    curl \
    libpq-dev \
    locales \
    python3-dev \
    rsync \
    tig \
    tmux \
    tzdata \
    vim

# Set timezone
RUN cp /usr/share/zoneinfo/Europe/Skopje /etc/localtime
RUN echo "Europe/Skopje" > /etc/timezone
ENV TZ=Europe/Skopje

# Setup normal user. If not passed as build argument use 'devel' as default
RUN addgroup --gid 1000 devel && \
    adduser --uid 1000 --ingroup devel --home /home/devel --shell /bin/bash --disabled-password --gecos "" devel

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# RUN pip install --upgrade pip

# Install dependencies
COPY requirements.txt .
RUN uv pip install --no-cache-dir -r requirements.txt --system

# Install fixuid
RUN USER=devel && \
    GROUP=devel && \
    curl -SsL https://github.com/boxboat/fixuid/releases/download/v0.5.1/fixuid-0.5.1-linux-amd64.tar.gz | tar -C /usr/local/bin -xzf - && \
    chown root:root /usr/local/bin/fixuid && \
    chmod 4755 /usr/local/bin/fixuid && \
    mkdir -p /etc/fixuid && \
    printf "user: $USER\ngroup: $GROUP\n" > /etc/fixuid/config.yml

# Switch to user
USER devel:devel

# Copy the application code
COPY . /project

# Install the application dependencies
WORKDIR /project
# RUN uv sync --frozen --no-cache

# Expose the port the app runs on
EXPOSE 8000

ENV PYTHONPATH=/project

# Export local user executables for python scripts
ENV PATH "$PATH:.venv/bin/:home/devel/.local/bin"

ENTRYPOINT ["fixuid"]


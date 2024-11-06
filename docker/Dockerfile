# FROM python:3.12.1-slim-bullseye
FROM ghcr.io/astral-sh/uv:python3.13-alpine

LABEL maintainer="Aleksandar Krsteski <aleksandar.krsteski@ved.mk>"
LABEL description="HTTP & WebSocket Handlers"

# General system staff
RUN apk update && apk upgrade && \
    apk add --no-cache \
    tzdata \
    bash \
    tmux \
    rsync \
    curl \
    tig \
    vim \
    build-base \
    python3-dev

# Set timezone
RUN cp /usr/share/zoneinfo/Europe/Skopje /etc/localtime
RUN echo "Europe/Skopje" > /etc/timezone
ENV TZ=Europe/Skopje

# Setup normal user. If not passed as build argument use 'devel' as default
RUN addgroup --gid 1000 devel && \
    adduser --uid 1000 --ingroup devel --home /home/devel --shell /bin/bash --disabled-password --gecos "" devel

RUN pip install --upgrade pip

# Install dependencies
COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt
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

WORKDIR /project

# Copy the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

ENV PYTHONPATH=/project

# Export local user executables for python scripts
ENV PATH "$PATH:/home/devel/.local/bin"

ENTRYPOINT ["fixuid"]


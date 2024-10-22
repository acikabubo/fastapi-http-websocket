FROM python:3.12.1-slim-bullseye

LABEL maintainer="Aleksandar Krsteski <aleksandar.krsteski@gmail.comved.mk>"
LABEL description="HTTP & WebSocket Handlers"

# General system staff
RUN apt update && apt-get upgrade -y && apt autoremove -y && \
    apt install -my locales tmux rsync curl tig vim build-essential

RUN echo 'Europe/Skopje' > /etc/timezone
ENV TZ=Europe/Skopje
RUN echo 'en_US.UTF-8 UTF-8' > /etc/locale.gen
RUN locale-gen

# Setup normal user. If not passed as build argument use 'devel' as default
RUN addgroup --gid 1000 devel && \
    adduser --uid 1000 --ingroup devel --home /home/devel --shell /bin/bash --disabled-password --gecos "" devel

RUN pip install --upgrade pip

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install fixuid
RUN USER=devel && \
    GROUP=devel && \
    curl -SsL https://github.com/boxboat/fixuid/releases/download/v0.5.1/fixuid-0.5.1-linux-amd64.tar.gz | tar -C /usr/local/bin -xzf - && \
    chown root:root /usr/local/bin/fixuid && \
    chmod 4755 /usr/local/bin/fixuid && \
    mkdir -p /etc/fixuid && \
    printf "user: $USER\ngroup: $GROUP\n" > /etc/fixuid/config.yml

WORKDIR /project

# Copy the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

ENV PYTHONPATH=/project

# Export local user executables for python scripts
ENV PATH "$PATH:/home/devel/.local/bin"

ENTRYPOINT ["fixuid"]


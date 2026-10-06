FROM jenkins/jenkins:lts-jdk17

COPY docker-compose-plugin /usr/local/lib/docker/cli-plugins/docker-compose

USER root

RUN apt-get update && apt-get install -y --no-install-recommends docker-cli python3 python3-venv python3-pip curl git && rm -rf /var/lib/apt/lists/* && docker --version

USER root

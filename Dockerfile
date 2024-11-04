FROM python:3.9.13-buster

ENV WORKDIR_PATH /usr/src/app
ENV DOCKER 1

RUN pip install pipenv

WORKDIR $WORKDIR_PATH

RUN mkdir ${DATA_DIR} ${TMP_DIR} .pytest_cache;

RUN apt-get update && \
    apt-get -qy full-upgrade && \
    apt-get install -qy curl && \
    curl -sSL https://get.docker.com/ | sh

RUN apt-get update && \
    apt-get install -y openjdk-11-jre-headless && \
    apt-get clean

COPY ./Pipfile* ./
RUN pipenv install --deploy --system --clear --dev

COPY . .

ARG SERVICE_NAME
RUN python shrink_env.py "$SERVICE_NAME"

CMD python main.py

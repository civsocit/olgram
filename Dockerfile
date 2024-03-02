FROM python:3.8-buster

ENV PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.5.1 \
    POETRY_VIRTUALENVS_CREATE="false"

RUN apt-get update && \
    apt-get install -y gettext build-essential && \
    apt-get clean && rm -rf /var/cache/apt/* && rm -rf /var/lib/apt/lists/* && rm -rf /tmp/*


RUN pip install "poetry==$POETRY_VERSION"

WORKDIR /app

COPY pyproject.toml poetry.lock docker-entrypoint.sh ./
RUN poetry install --no-interaction --no-ansi --no-dev

COPY . /app

RUN msgfmt locales/zh/LC_MESSAGES/olgram.po -o locales/zh/LC_MESSAGES/olgram.mo --use-fuzzy
RUN msgfmt locales/uk/LC_MESSAGES/olgram.po -o locales/uk/LC_MESSAGES/olgram.mo --use-fuzzy
RUN msgfmt locales/en/LC_MESSAGES/olgram.po -o locales/en/LC_MESSAGES/olgram.mo --use-fuzzy

EXPOSE 80

ENTRYPOINT ["./docker-entrypoint.sh"]

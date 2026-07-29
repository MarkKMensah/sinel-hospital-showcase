FROM python:3.12-slim AS wheels

ARG PIP_VERSION=26.1.2
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m pip install --no-cache-dir --upgrade "pip==$PIP_VERSION"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libjpeg62-turbo-dev \
        libpq-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels
COPY requirements.txt .
RUN python -m pip wheel --no-cache-dir --wheel-dir /wheels/dist -r requirements.txt

FROM python:3.12-slim

ARG PIP_VERSION=26.1.2
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV APP_HOME=/home/sinel_web/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        libpq5 \
        netcat-openbsd \
        zlib1g \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system sinel_web \
    && adduser --system --ingroup sinel_web --home /home/sinel_web sinel_web \
    && mkdir -p "$APP_HOME"

RUN python -m pip install --no-cache-dir --upgrade "pip==$PIP_VERSION"

WORKDIR $APP_HOME

COPY requirements.txt .
COPY --from=wheels /wheels/dist /wheels
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

COPY entrypoint.sh .
RUN sed -i 's/\r$//g' entrypoint.sh \
    && chmod +x entrypoint.sh

COPY . .
RUN chown -R sinel_web:sinel_web /home/sinel_web

USER sinel_web

ENTRYPOINT ["/home/sinel_web/app/entrypoint.sh"]

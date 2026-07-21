FROM python:3.12-slim


ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


WORKDIR /app


RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .


RUN pip install --upgrade pip \
    && pip install --no-cache-dir \
    -r requirements.txt


COPY . .


RUN chmod +x /app/entrypoint.sh


RUN addgroup --system django \
    && adduser --system --ingroup django django


RUN chown -R django:django /app


USER django

ENTRYPOINT ["/app/entrypoint.sh"]
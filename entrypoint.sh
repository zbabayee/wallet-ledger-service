#!/bin/sh

set -e

echo "Waiting for postgres..."

until nc -z "$DB_HOST" "$DB_PORT"
do
    sleep 1
done

echo "PostgreSQL started"

python manage.py collectstatic --noinput

exec "$@"
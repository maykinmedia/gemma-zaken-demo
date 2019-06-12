#!/bin/sh

set -ex

# Wait for the database container
# See: https://docs.docker.com/compose/startup-order/
db_host=${DB_HOST:-db}
db_user=${DB_USER:-postgres}
db_password=${DB_PASSWORD}
db_port=${DB_PORT:-5432}

asgi_port=${ASGI_PORT:-8000}

until PGPORT=$db_port PGPASSWORD=$db_password psql -h "$db_host" -U "$db_user" -c '\q'; do
  >&2 echo "Waiting for database connection..."
  sleep 1
done

>&2 echo "Database is up."

# Apply database migrations
>&2 echo "Apply database migrations"
python src/manage.py migrate

# check if we need to run collectstatic (volume overwrites image content)
target=/app/static
if [ "$(find "$target" -mindepth 1 -print -quit 2>/dev/null)" ]; then
    echo "Not empty, skipping"
else
    python src/manage.py collectstatic --noinput
fi

# Start server
>&2 echo "Starting server"
cd src
daphne -p $asgi_port -b 0.0.0.0 zac.asgi:application

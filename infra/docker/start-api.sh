#!/bin/sh
set -eu
umask 022
python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec "$@"

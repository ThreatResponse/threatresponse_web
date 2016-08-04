#!/bin/bash
cd /app
chmod -R 777 /tmp
chown -R celery-worker:celery-worker /app
chgrp celery-worker /var/run/docker.sock
su celery-worker -c 'celery -A threatresponse.tasks worker' &
su celery-worker -c 'exec gunicorn -w 1 --bind 0.0.0.0:9999 -m 007 wsgi:app'

#!/bin/bash

celery -A config worker -l info -c 4 -P gevent

exit $?

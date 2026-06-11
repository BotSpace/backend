#!/bin/bash

# Real-time kollaboratsiya op'larini Redis'dan o'qib project.flow'ga saqlaydi.
python3 manage.py collab_persist_worker

exit $?

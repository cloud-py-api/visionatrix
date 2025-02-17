#!/bin/bash

if ! nc -z 127.0.0.1 8288; then
  echo "ERROR: Visionatrix not responding on 127.0.0.1:8288"
  exit 1
fi

exit 0

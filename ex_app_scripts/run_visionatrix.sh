#!/bin/sh

. /etc/environment

if [ "$DISABLE_WORKER" != "1" ]; then
    /Visionatrix/venv/bin/python -m visionatrix run --mode=SERVER > /server.log 2>&1 &
    sleep 15
    /Visionatrix/venv/bin/python -m visionatrix run --mode=WORKER --disable-smart-memory > /worker.log 2>&1
else
    VIX_SERVER_FULL_MODELS=0 /Visionatrix/venv/bin/python -m visionatrix run --mode=SERVER > /server.log 2>&1
fi

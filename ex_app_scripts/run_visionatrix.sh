#!/bin/sh

. /etc/environment

if [ "$DISABLE_WORKER" != "1" ]; then
    /Visionatrix/venv/bin/python -m visionatrix run --mode=SERVER --disable-smart-memory &
    sleep 15
    /Visionatrix/venv/bin/python -m visionatrix run --mode=WORKER --disable-smart-memory
else
    VIX_SERVER_FULL_MODELS=0 /Visionatrix/venv/bin/python -m visionatrix run --mode=SERVER --disable-smart-memory
fi

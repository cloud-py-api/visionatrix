FROM python:3.10-slim

ENV VIX_HOST "127.0.0.1"
ENV VIX_PORT 8288
ENV USER_BACKENDS "nextcloud"
ARG COMPUTE_DEVICE="CUDA"

RUN apt-get update && apt-get install -y git \
	python3-dev python3-setuptools netcat-traditional \
	libxml2-dev libxslt1-dev zlib1g-dev g++ \
	ffmpeg libsm6 libxext6

WORKDIR /app/service

RUN python3 -m venv venv && venv/bin/python -m pip install -U pip && rm -rf ~/.cache/pip

RUN if [ "$COMPUTE_DEVICE" = "CUDA" ]; then \
	venv/bin/python -m pip install -U torch torchvision --extra-index-url https://download.pytorch.org/whl/cu121 \
	&& rm -rf ~/.cache/pip; \
elif [ "$COMPUTE_DEVICE" = "ROCM" ]; then \
	venv/bin/python -m pip install -U --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/rocm6.0 \
	&& rm -rf ~/.cache/pip; \
elif [ "$COMPUTE_DEVICE" = "CPU" ]; then \
	venv/bin/python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu \
	&& rm -rf ~/.cache/pip; \
fi

RUN git clone --depth 1 https://github.com/Visionatrix/Visionatrix.git

RUN venv/bin/python -m pip install ./Visionatrix \
	&& venv/bin/python -m visionatrix install \
	&& rm -rf ~/.cache/pip

# Setup nodejs and npm for building the front-end client
RUN apt-get update && \
    apt-get install -y curl gnupg2 build-essential supervisor && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install dependncies, build the client and remove node_modules
RUN cd Visionatrix/web && npm install && cd ../ && make build-client-nextcloud && rm -rf ./web/node_modules

# Remove nodejs and npm and clean cache
RUN apt-get remove -y nodejs npm && apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/* && rm -rf ~/.cache

# Setup ExApp dependencies
COPY requirements.txt /
RUN python3 -m pip install -r /requirements.txt && rm -rf ~/.cache && rm /requirements.txt

ADD cs[s] /app/css
ADD im[g] /app/img
ADD j[s] /app/js
ADD l10[n] /app/l10n
ADD li[b] /app/lib

RUN mkdir -p /var/log/supervisor
RUN mkdir -p /etc/supervisor/conf.d
COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY vix.conf /etc/supervisor/conf.d/vix.conf
COPY vix_service.conf /etc/supervisor/conf.d/vix_service.conf

RUN mkdir -p /nc_app_vix_data/vix_flows && mkdir -p /nc_app_vix_data/vix_models && mkdir -p /nc_app_vix_data/vix_tasks_files

ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]

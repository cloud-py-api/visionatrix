FROM python:3.10-slim

ARG BUILD_TYPE

# Visionatrix enviroment variables
ENV VIX_HOST="127.0.0.1"
ENV VIX_PORT=8288
ENV USER_BACKENDS="vix_db;nextcloud"
ENV FLOWS_DIR="/nc_app_vix_data/vix_flows"
ENV MODELS_DIR="/nc_app_vix_data/vix_models"
ENV TASKS_FILES_DIR="/nc_app_vix_data/vix_tasks_files"
ENV BACKEND_DIR="/Visionatrix/vix_backend"
ENV VIX_SERVER_FULL_MODELS="1"

RUN apt-get update && apt-get install -y git \
	python3-dev python3-setuptools netcat-traditional \
	libxml2-dev libxslt1-dev zlib1g-dev g++ \
	ffmpeg libsm6 libxext6 lsb-release sudo wget procps nano xmlstarlet

COPY appinfo/info.xml /info.xml

RUN VISIONATRIX_VERSION=$(xmlstarlet sel -t -v "//image-tag" /info.xml) && \
    git clone https://github.com/Visionatrix/Visionatrix.git /Visionatrix && \
    cd /Visionatrix && \
    git checkout tags/v$VISIONATRIX_VERSION && \
    rm /info.xml

RUN cd /Visionatrix && python3 -m venv venv && venv/bin/python -m pip install -U pip && rm -rf ~/.cache/pip

RUN cd /Visionatrix && \
    ARCH=$(uname -m) && \
    if [ "$ARCH" = "aarch64" ]; then \
        echo "Installing PyTorch for ARM64"; \
        venv/bin/python -m pip install torch torchvision torchaudio; \
    elif [ "$BUILD_TYPE" = "rocm" ]; then \
        venv/bin/python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.1; \
    elif [ "$BUILD_TYPE" = "cpu" ]; then \
        venv/bin/python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu; \
    else \
        venv/bin/python -m pip install torch torchvision torchaudio; \
    fi && \
	rm -rf ~/.cache/pip

RUN cd /Visionatrix && \
    venv/bin/python -m pip install "psycopg[binary]" greenlet && \
    venv/bin/python -m pip install . && \
	venv/bin/python -m visionatrix install && \
	rm -rf ~/.cache/pip

# Setup nodejs and npm for building the front-end client
RUN apt-get update && \
    apt-get install -y curl gnupg2 build-essential supervisor && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install dependncies, build the client and remove node_modules
RUN cd /Visionatrix && \
    rm -rf visionatrix/client && \
    cd web && \
    npm install && \
    NUXT_APP_BASE_URL="/index.php/apps/app_api/proxy/visionatrix/" npm run build && \
	cp -r .output/public ../visionatrix/client && \
    rm -rf node_modules

# Remove nodejs and npm and clean cache
 RUN apt-get remove -y nodejs npm && apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/* && rm -rf ~/.cache

# Setup ExApp dependencies
COPY ex_app_scripts/init_pgsql.sh /ex_app_scripts/init_pgsql.sh
COPY ex_app_scripts/entrypoint.sh /ex_app_scripts/entrypoint.sh

RUN chmod +x /ex_app_scripts/*.sh

COPY requirements.txt /
RUN python3 -m pip install -r /requirements.txt && rm -rf ~/.cache && rm /requirements.txt

ADD /ex_app/cs[s] /ex_app/css
ADD /ex_app/im[g] /ex_app/img
ADD /ex_app/j[s] /ex_app/js
ADD /ex_app/l10[n] /ex_app/l10n
ADD /ex_app/li[b] /ex_app/lib

WORKDIR /Visionatrix

CMD ["/bin/sh", \
	"/ex_app_scripts/entrypoint.sh", \
	"/ex_app/lib/main.py", \
	"/ex_app_scripts/run_visionatrix.sh"]

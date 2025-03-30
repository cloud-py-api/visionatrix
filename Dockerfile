FROM python:3.12-slim

ARG BUILD_TYPE

# Visionatrix enviroment variables
ENV VIX_HOST="127.0.0.1"
ENV VIX_PORT=8288
ENV USER_BACKENDS="vix_db;nextcloud"
ENV BASE_DATA_DIR="/nc_app_visionatrix_data"
ENV VIX_SERVER_FULL_MODELS="1"

RUN apt-get update && apt-get install -y git \
	python3-dev python3-setuptools netcat-traditional \
	libxml2-dev libxslt1-dev zlib1g-dev g++ \
	ffmpeg libsm6 libxext6 lsb-release sudo wget procps nano xmlstarlet curl && \
    apt-get autoclean

# HaRP: download and install FRP client
RUN set -ex; \
    ARCH=$(uname -m); \
    if [ "$ARCH" = "aarch64" ]; then \
      FRP_URL="https://raw.githubusercontent.com/nextcloud/HaRP/main/exapps_dev/frp_0.61.1_linux_arm64.tar.gz"; \
    else \
      FRP_URL="https://raw.githubusercontent.com/nextcloud/HaRP/main/exapps_dev/frp_0.61.1_linux_amd64.tar.gz"; \
    fi; \
    echo "Downloading FRP client from $FRP_URL"; \
    curl -L "$FRP_URL" -o /tmp/frp.tar.gz; \
    tar -C /tmp -xzf /tmp/frp.tar.gz; \
    mv /tmp/frp_0.61.1_linux_* /tmp/frp; \
    cp /tmp/frp/frpc /usr/local/bin/frpc; \
    chmod +x /usr/local/bin/frpc; \
    rm -rf /tmp/frp /tmp/frp.tar.gz

ADD ex_app_scripts/common_pgsql.sh /ex_app_scripts/
RUN chmod +x /ex_app_scripts/common_pgsql.sh

ADD ex_app_scripts/install_pgsql.sh /ex_app_scripts/
RUN chmod +x /ex_app_scripts/install_pgsql.sh && /ex_app_scripts/install_pgsql.sh && rm /ex_app_scripts/install_pgsql.sh

COPY appinfo/info.xml /info.xml

RUN VISIONATRIX_VERSION=$(xmlstarlet sel -t -v "//image-tag" /info.xml) && \
    git clone https://github.com/Visionatrix/Visionatrix.git /Visionatrix && \
    cd /Visionatrix && \
    git checkout tags/v$VISIONATRIX_VERSION && \
    rm /info.xml

RUN --mount=type=cache,target=/root/.cache/pip \
    cd /Visionatrix && python3 -m venv venv && venv/bin/python -m pip install -U pip

RUN --mount=type=cache,target=/root/.cache/pip \
    cd /Visionatrix && \
    ARCH=$(uname -m) && \
    if [ "$ARCH" = "aarch64" ]; then \
        echo "Installing PyTorch for ARM64"; \
        venv/bin/python -m pip install torch==2.6.0 torchvision torchaudio; \
    elif [ "$BUILD_TYPE" = "rocm" ]; then \
        venv/bin/python -m pip install torch==2.6.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.2.4; \
    elif [ "$BUILD_TYPE" = "cpu" ]; then \
        venv/bin/python -m pip install torch==2.6.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu; \
    else \
        venv/bin/python -m pip install torch==2.6.0 torchvision torchaudio; \
    fi

RUN --mount=type=cache,target=/root/.cache/pip \
    cd /Visionatrix && \
    venv/bin/python -m pip install "psycopg[binary]" greenlet && \
    venv/bin/python -m pip install . && \
    venv/bin/python -m visionatrix install && \
    rm visionatrix.db

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
    npm ci && \
    NUXT_APP_BASE_URL="/exapps/visionatrix/" NEXTCLOUD_INTEGRATION=true npm run build && \
    cp -r .output/public ../visionatrix/client_harp && \
    NUXT_APP_BASE_URL="/index.php/apps/app_api/proxy/visionatrix/" NEXTCLOUD_INTEGRATION=true npm run build && \
	cp -r .output/public ../visionatrix/client && \
    rm -rf node_modules

# Remove nodejs and npm and clean cache
RUN apt-get remove -y nodejs npm && apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/* && rm -rf ~/.cache

# Setup ExApp dependencies
COPY ex_app_scripts/init_pgsql.sh /ex_app_scripts/init_pgsql.sh
COPY ex_app_scripts/entrypoint.sh /ex_app_scripts/entrypoint.sh

RUN chmod +x /ex_app_scripts/*.sh

COPY requirements.txt /
RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -m pip install -r /requirements.txt && rm /requirements.txt

ADD /ex_app/cs[s] /ex_app/css
ADD /ex_app/im[g] /ex_app/img
ADD /ex_app/j[s] /ex_app/js
ADD /ex_app/js_har[p] /ex_app/js_harp
ADD /ex_app/l10[n] /ex_app/l10n
ADD /ex_app/li[b] /ex_app/lib

COPY --chmod=775 healthcheck.sh /

WORKDIR /Visionatrix

CMD ["/bin/sh", \
	"/ex_app_scripts/entrypoint.sh", \
	"/ex_app/lib/main.py"]

HEALTHCHECK --interval=5s --timeout=2s --retries=300 CMD /healthcheck.sh

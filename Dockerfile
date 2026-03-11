# syntax=docker/dockerfile:1
# check=skip=SecretsUsedInArgOrEnv

ARG PYTHON_VERSION=3.10
ARG BASE_IMAGE=python:${PYTHON_VERSION}-slim-trixie

ARG DEBIAN_FRONTEND=noninteractive
ARG FOT_API_SLUG="rest-fastapi-orm-template"


## Here is the builder image:
FROM ${BASE_IMAGE} AS builder

ARG DEBIAN_FRONTEND
ARG FOT_API_SLUG

ENV	UV_LINK_MODE=copy

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR "/usr/src/${FOT_API_SLUG}"

RUN --mount=type=cache,target=/root/.cache,sharing=locked \
	_BUILD_TARGET_ARCH=$(uname -m) && \
	echo "BUILDING TARGET ARCHITECTURE: ${_BUILD_TARGET_ARCH}" && \
	rm -rfv /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* && \
	apt-get clean -y && \
	# echo "Acquire::http::Pipeline-Depth 0;" >> /etc/apt/apt.conf.d/99fixbadproxy && \
	# echo "Acquire::http::No-Cache true;" >> /etc/apt/apt.conf.d/99fixbadproxy && \
	# echo "Acquire::BrokenProxy true;" >> /etc/apt/apt.conf.d/99fixbadproxy && \
	apt-get update --fix-missing -o Acquire::CompressionTypes::Order::=gz && \
	apt-get install -y --no-install-recommends \
		build-essential \
		libpq-dev && \
	python3 -m pip install --timeout 60 -U pip uv

# COPY ./requirements* ./
RUN	--mount=type=cache,target=/root/.cache,sharing=locked \
	--mount=type=bind,source=requirements.txt,target=requirements.txt \
	python3 -m uv pip install --prefix=/install -r ./requirements.txt


## Here is the base image:
FROM ${BASE_IMAGE} AS base

ARG DEBIAN_FRONTEND
ARG FOT_API_SLUG

ARG FOT_HOME_DIR="/app"
ARG FOT_API_DIR="${FOT_HOME_DIR}/${FOT_API_SLUG}"
ARG FOT_API_CONFIGS_DIR="/etc/${FOT_API_SLUG}"
ARG FOT_API_DATA_DIR="/var/lib/${FOT_API_SLUG}"
ARG FOT_API_LOGS_DIR="/var/log/${FOT_API_SLUG}"
ARG FOT_API_TMP_DIR="/tmp/${FOT_API_SLUG}"
ARG FOT_API_PORT=8000
ARG FOT_API_DOCS_ENABLED=false
## echo "FOT_USER_PASSWORD123" | openssl passwd -6 -stdin
ARG HASH_PASSWORD="\$6\$KTocg05KixrDJ/fk\$zROBplLOs/AuvRPmcKM88crNFcZoBKDXTQrEjPAoB3DM9qMaQSf6n6DsA47hiiZDOPJRt0ispphQMqP10e01I."
ARG UID=1000
ARG GID=11000
ARG USER=fot-user
ARG GROUP=fot-group

ENV FOT_API_SLUG="${FOT_API_SLUG}" \
	FOT_HOME_DIR="${FOT_HOME_DIR}" \
	FOT_API_DIR="${FOT_API_DIR}" \
	FOT_API_CONFIGS_DIR="${FOT_API_CONFIGS_DIR}" \
	FOT_API_DATA_DIR="${FOT_API_DATA_DIR}" \
	FOT_API_LOGS_DIR="${FOT_API_LOGS_DIR}" \
	FOT_API_TMP_DIR="${FOT_API_TMP_DIR}" \
	FOT_API_PORT=${FOT_API_PORT} \
	FOT_API_DOCS_ENABLED=${FOT_API_DOCS_ENABLED} \
	UID=${UID} \
	GID=${GID} \
	USER=${USER} \
	GROUP=${GROUP} \
	PYTHONIOENCODING=utf-8 \
	PYTHONUNBUFFERED=1

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN --mount=type=secret,id=HASH_PASSWORD \
	rm -vrf /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* /root/.cache/* && \
	apt-get clean -y && \
	# echo "Acquire::http::Pipeline-Depth 0;" >> /etc/apt/apt.conf.d/99fixbadproxy && \
	# echo "Acquire::http::No-Cache true;" >> /etc/apt/apt.conf.d/99fixbadproxy && \
	# echo "Acquire::BrokenProxy true;" >> /etc/apt/apt.conf.d/99fixbadproxy && \
	apt-get update --fix-missing -o Acquire::CompressionTypes::Order::=gz && \
	apt-get install -y --no-install-recommends \
		sudo \
		gosu \
		locales \
		tzdata \
		procps \
		iputils-ping \
		iproute2 \
		curl \
		nano \
		libpq5 && \
	apt-get clean -y && \
	sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
	sed -i -e 's/# en_AU.UTF-8 UTF-8/en_AU.UTF-8 UTF-8/' /etc/locale.gen && \
	sed -i -e 's/# ko_KR.UTF-8 UTF-8/ko_KR.UTF-8 UTF-8/' /etc/locale.gen && \
	dpkg-reconfigure --frontend=noninteractive locales && \
	update-locale LANG=en_US.UTF-8 && \
	echo "LANGUAGE=en_US.UTF-8" >> /etc/default/locale && \
	echo "LC_ALL=en_US.UTF-8" >> /etc/default/locale && \
	addgroup --gid ${GID} ${GROUP} && \
	useradd -lmN -d "/home/${USER}" -s /bin/bash -g ${GROUP} -G sudo -u ${UID} ${USER} && \
	# echo "${USER} ALL=(ALL) NOPASSWD: ALL" > "/etc/sudoers.d/${USER}" && \
	# chmod 0440 "/etc/sudoers.d/${USER}" && \
	if [ -f "/run/secrets/HASH_PASSWORD" ]; then \
		echo "Using hashed password from secret: /run/secrets/HASH_PASSWORD"; \
		echo -e "${USER}:$(cat /run/secrets/HASH_PASSWORD)" | chpasswd -e; \
	else \
		echo "Using hashed password from build argument: HASH_PASSWORD"; \
		echo -e "${USER}:${HASH_PASSWORD}" | chpasswd -e; \
	fi && \
	echo -e "\nalias ls='ls -aF --group-directories-first --color=auto'" >> /root/.bashrc && \
	echo -e "alias ll='ls -alhF --group-directories-first --color=auto'\n" >> /root/.bashrc && \
	echo -e "\numask 0002" >> "/home/${USER}/.bashrc" && \
	echo "alias ls='ls -aF --group-directories-first --color=auto'" >> "/home/${USER}/.bashrc" && \
	echo -e "alias ll='ls -alhF --group-directories-first --color=auto'\n" >> "/home/${USER}/.bashrc" && \
	rm -rfv /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* /root/.cache/* "/home/${USER}/.cache/*" && \
	mkdir -pv "${FOT_API_DIR}" \
		"${FOT_API_CONFIGS_DIR}" \
		"${FOT_API_DATA_DIR}" \
		"${FOT_API_LOGS_DIR}" \
		"${FOT_API_TMP_DIR}" && \
	chown -Rc "${USER}:${GROUP}" \
		"${FOT_HOME_DIR}" \
		"${FOT_API_CONFIGS_DIR}" \
		"${FOT_API_DATA_DIR}" \
		"${FOT_API_LOGS_DIR}" \
		"${FOT_API_TMP_DIR}" && \
	find "${FOT_API_DIR}" "${FOT_API_CONFIGS_DIR}" "${FOT_API_DATA_DIR}" -type d -exec chmod -c 770 {} + && \
	find "${FOT_API_DIR}" "${FOT_API_CONFIGS_DIR}" "${FOT_API_DATA_DIR}" -type d -exec chmod -c ug+s {} + && \
	find "${FOT_API_LOGS_DIR}" "${FOT_API_TMP_DIR}" -type d -exec chmod -c 775 {} + && \
	find "${FOT_API_LOGS_DIR}" "${FOT_API_TMP_DIR}" -type d -exec chmod -c +s {} +

ENV LANG=en_US.UTF-8 \
	LANGUAGE=en_US.UTF-8 \
	LC_ALL=en_US.UTF-8

COPY --from=builder --chown=${UID}:${GID} /install /usr/local


## Here is the final image:
FROM base AS app

WORKDIR "${FOT_API_DIR}"
COPY --chown=${UID}:${GID} ./src ${FOT_API_DIR}
COPY --chown=${UID}:${GID} --chmod=770 ./scripts/docker/*.sh /usr/local/bin/

# VOLUME ["${FOT_API_DATA_DIR}"]
# EXPOSE ${FOT_API_PORT}

# USER ${UID}:${GID}
# HEALTHCHECK --start-period=30s --start-interval=1s --interval=5m --timeout=5s --retries=3 \
# 	CMD curl -f http://localhost:${FOT_API_PORT}/api/v${FOT_API_VERSION:-1}/ping || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
# CMD ["-b", "uvicorn api.main:app --host=0.0.0.0 --port=${FOT_API_PORT:-8000} --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips='*'"]

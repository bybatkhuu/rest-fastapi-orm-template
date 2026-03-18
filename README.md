# FastAPI ORM Template

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/bybatkhuu/rest-fastapi-orm-template/3.create-release.yml?logo=GitHub)](https://github.com/bybatkhuu/rest-fastapi-orm-template/actions/workflows/3.create-release.yml)
[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/bybatkhuu/rest-fastapi-orm-template?logo=GitHub)](https://github.com/bybatkhuu/rest-fastapi-orm-template/releases)

This is a template repository for FastAPI with ORM (SQLAlchemy) projects.

## ✨ Features

- FastAPI
- REST API
- Web service
- Microservice
- ORM (SQLAlchemy)
- SQL databases (RDB)
- Database migrations (Alembic)
- PostgreSQL
- Configuration

---

## 🐤 Getting Started

### 1. 🚧 Prerequisites

[RECOMMENDED] For **docker** runtime:

- Install [**docker** and **docker compose**](https://docs.docker.com/engine/install)
    - Docker image: [**bybatkhuu/rest-fastapi-orm-template**](https://hub.docker.com/r/bybatkhuu/rest-fastapi-orm-template)

For **standalone** runtime:

- Install **Python (>= v3.10)** and **pip (>= 23)**:
    - **[RECOMMENDED] [Miniconda (v3)](https://www.anaconda.com/docs/getting-started/miniconda/install)**
    - *[arm64/aarch64] [Miniforge (v3)](https://github.com/conda-forge/miniforge)*
    - *[Python virtual environment] [venv](https://docs.python.org/3/library/venv.html)*
- Install **PostrgreSQL (>= v18)**:
    - **[RECOMMENDED] [Docker image](https://hub.docker.com/_/postgres)** (postgres)
    - *[Packages and installers](https://www.postgresql.org/download)*
- Install **libpq (>= v17)** for **psycopg[c]**:
    - **[RECOMMENDED] Miniconda - [libpq](https://anaconda.org/anaconda/libpq)**
    - Debian/Ubuntu - **libpq-dev**
    - MacOS - **[libpq](https://formulae.brew.sh/formula/libpq)**

[OPTIONAL] For **DEVELOPMENT** environment:

- Install [**git**](https://git-scm.com/downloads)
- Setup an [**SSH key**](https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh)

### 2. 📥 Download or clone the repository

**2.1.** Prepare projects directory (if not exists):

```sh
# Create projects directory:
mkdir -pv ~/workspaces/projects

# Enter into projects directory:
cd ~/workspaces/projects
```

**2.2.** Follow one of the below options **[A]**, **[B]** or **[C]**:

**OPTION A.** Clone the repository:

```sh
git clone https://github.com/bybatkhuu/rest-fastapi-orm-template.git && \
    cd rest-fastapi-orm-template
```

**OPTION B.** Clone the repository (for **DEVELOPMENT**: git + ssh key):

```sh
git clone git@github.com:bybatkhuu/rest-fastapi-orm-template.git && \
    cd rest-fastapi-orm-template
```

**OPTION C.** Download source code:

1. Download archived **zip** or **tar.gz** file from [**releases**](https://github.com/bybatkhuu/rest-fastapi-orm-template/releases).
2. Extract it into the projects directory.
3. Enter into the project directory.

### 3. 📦 Install dependencies

[TIP] Skip this step, if you're going to use **docker** runtime

<!-- #### 3.1. Install base/common dependencies -->

```sh
pip install -r ./requirements.txt

# For DEVELOPMENT:
pip install -r ./requirements/requirements.dev.txt
# Install pre-commit hooks:
pre-commit install
```

<!-- #### 3.2. Install hardware specific dependencies

Follow the one of below instructions based on your environment (A is recommended for most cases):

**OPTION A.** For Intel/AMD **x86_64** CPU:

```sh
pip install -r ./requirements/requirements.amd64.txt
```

**OPTION B.** For **arm64/aarch64** CPU:

```sh
pip install -r ./requirements/requirements.arm64.txt
``` -->

### 4. 🌎 Configure environment variables

[NOTE] Please, check **[environment variables](#-environment-variables)** section for more details.

```sh
# Copy '.env.example' file to '.env' file:
cp -v ./.env.example ./.env
# Edit environment variables to fit in your environment:
nano ./.env
```

### 5. 🏁 Start the server

[NOTE] Follow the one of below instructions based on your environment **[A, B, C, D, E]**:

#### Docker runtime

**OPTION A.** **[RECOMMENDED]** Run with **docker compose**:

```sh
## 1. Configure 'compose.override.yml' file.
# Copy 'compose.override.[ENV].yml' file to 'compose.override.yml' file:
cp -v ./templates/compose/compose.override.[ENV].yml ./compose.override.yml
# For example, DEVELOPMENT environment:
cp -v ./templates/compose/compose.override.dev.yml ./compose.override.yml
# For example, STATGING or PRODUCTION environment:
cp -v ./templates/compose/compose.override.prod.yml ./compose.override.yml
# Edit 'compose.override.yml' file to fit in your environment:
nano ./compose.override.yml

## 2. Check docker compose configuration is valid:
./compose.sh validate
# Or:
docker compose config

## 3. Start docker compose:
./compose.sh start -l
# Or:
docker compose up -d --remove-orphans --force-recreate && \
    docker compose logs -f -n 100
```

#### Standalone runtime

[**IMPORTANT**] Before running, make sure **database** is up and running.

Run `alembic migration` to create or update `database schema` to the latest version:

```sh
./scripts/migrate.sh up

# Or directly with alembic command:
ln -s -v ../.env ./src/.env
cd ./src
alembic -x data=true upgrade head
cd ..
```

**OPTION B.** Run with **PM2**:

[**IMPORTANT**] Before running, need to install [**PM2**](https://pm2.keymetrics.io/docs/usage/quick-start):

```sh
## 1. Configure PM2 configuration file.
# Copy example PM2 configuration file:
cp -v ./pm2-process.json.example ./pm2-process.json
# Edit PM2 configuration file to fit in your environment:
nano ./pm2-process.json

## 2. Start PM2 process:
pm2 start ./pm2-process.json && \
    pm2 logs --lines 50 fot
```

**OPTION C.** Run server as **python module**:

```sh
python -u -m src.api
```

**OPTION D.** Run with **uvicorn** cli:

```sh
uvicorn src.api.main:app --host=[BIND_HOST] --port=[PORT] --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips="*"
# For example:
uvicorn src.api.main:app --host="0.0.0.0" --port=8000 --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips="*"

# For DEVELOPMENT:
uvicorn src.api.main:app --host="0.0.0.0" --port=8000 --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips="*" --reload --reload-dir=./src
```

**OPTION E.** Run with **fastapi** cli:

```sh
fastapi run src/api/main.py --host=[BIND_HOST] --port=[PORT] --forwarded-allow-ips="*"
# For example:
fastapi run src/api/main.py --port=8000 --forwarded-allow-ips="*"

# For DEVELOPMENT:
fastapi dev src/api/main.py --host="0.0.0.0" --port=8000 --forwarded-allow-ips="*"
```

### 6. ✅ Check server is running

Check with CLI (curl):

```sh
# Send a ping request with 'curl' to REST API server and parse JSON response with 'jq':
curl -s http://localhost:8000/api/v1/ping | jq
```

Check with web browser:

- Health check: <http://localhost:8000/api/v1/health>
- Swagger: <http://localhost:8000/docs>
- Redoc: <http://localhost:8000/redoc>
- OpenAPI JSON: <http://localhost:8000/openapi.json>

### 7. 🛑 Stop the server

Docker runtime:

```sh
# Stop docker compose:
./compose.sh stop
# Or:
docker compose down --remove-orphans
```

Standalone runtime (Only for **PM2**):

```sh
pm2 stop ./pm2-process.json && \
    pm2 flush fot && \
    pm2 delete ./pm2-process.json
```

👍

---

## ⚙️ Configuration

### 🌎 Environment Variables

[**`.env.example`**](./.env.example):

```sh
## --- Environment variable --- ##
ENV=LOCAL
DEBUG=false
# TZ=UTC
# PYTHONDONTWRITEBYTECODE=1


## --- DB configs --- ##
FOT_DB_HOST=localhost # For local docker-compose: db
FOT_DB_PORT=5432
FOT_DB_USERNAME=fot_admin
FOT_DB_PASSWORD="FOT_DB_PASSWORD123" # !!! CHANGE THIS TO RANDOM PASSWORD !!! # pragma: allowlist secret
FOT_DB_DATABASE=fot_db
# FOT_DB_DSN_URL="postgresql+psycopg://fot_admin:FOT_DB_PASSWORD123@localhost:5432/fot_db" # !!! CHANGE THIS TO REAL DSN URL !!! # pragma: allowlist secret

# FOT_DB_READ_HOST=localhost
# FOT_DB_READ_PORT=5432
# FOT_DB_READ_USERNAME=fot_admin
# FOT_DB_READ_PASSWORD="FOT_DB_PASSWORD123" # !!! CHANGE THIS TO RANDOM PASSWORD !!! # pragma: allowlist secret
# FOT_DB_READ_DATABASE=fot_db
# FOT_DB_READ_DSN_URL="postgresql+psycopg://fot_admin:FOT_DB_PASSWORD123@localhost:5432/fot_db" # !!! CHANGE THIS TO REAL DSN URL !!! # pragma: allowlist secret


## -- API configs -- ##
FOT_API_PORT=8000
# FOT_API_CONFIGS_DIR="/etc/rest-fastapi-orm-template"
# FOT_API_LOGS_DIR="/var/log/rest-fastapi-orm-template"
# FOT_API_DATA_DIR="/var/lib/rest-fastapi-orm-template"
# FOT_API_TMP_DIR="/tmp/rest-fastapi-orm-template"
# FOT_API_VERSION="1"
# FOT_API_PREFIX="/api/v{api_version}"
# FOT_API_DOCS_ENABLED=true
# FOT_API_DOCS_OPENAPI_URL="{api_prefix}/openapi.json"
# FOT_API_DOCS_DOCS_URL="{api_prefix}/docs"
# FOT_API_DOCS_REDOC_URL="{api_prefix}/redoc"



## -- Extra -- ##
# FOT_DB_ECHO_SQL=false
# FOT_DB_ECHO_POOL=false
```

---

## 🧪 Running Tests

To run tests, run the following command:

```sh
# Install python test dependencies:
pip install -r ./requirements/requirements.test.txt

# Run tests:
./scripts/test.sh -l -v -c
# Or:
python -m pytest -sv -o log_cli=true
```

## 🏗️ Build Docker Image

Before building the docker image, make sure you have installed **docker** and **docker compose**.

To build the docker image, run the following command:

```sh
# Build docker image:
./scripts/build.sh
# Or:
docker compose build
```

## 📝 Generate Docs

To build the documentation, run the following command:

```sh
# Install python documentation dependencies:
pip install -r ./requirements/requirements.docs.txt

# Serve documentation locally (for development):
./scripts/docs.sh
# Or:
mkdocs serve -a 0.0.0.0:8000 --livereload

# Or build documentation:
./scripts/docs.sh -b
# Or:
mkdocs build
```

## 📚 Documentation

- [Docs](./docs)

---

## 📑 References

- FastAPI - <https://fastapi.tiangolo.com>
- PostgreSQL - <https://www.postgresql.org>
- SQLAlchemy - <https://www.sqlalchemy.org>
- Alembic - <https://alembic.sqlalchemy.org>
- Docker - <https://docs.docker.com>
- Docker Compose - <https://docs.docker.com/compose>

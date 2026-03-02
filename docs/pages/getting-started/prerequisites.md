# 🚧 Prerequisites

[RECOMMENDED] For **docker** runtime:

- Install [**docker** and **docker compose**](https://docs.docker.com/engine/install)
    - Docker image: [**bybatkhuu/rest-fastapi-orm-template**](https://hub.docker.com/r/bybatkhuu/rest-fastapi-orm-template)

For **standalone** runtime:

- Install **Python (>= v3.9)** and **pip (>= 23)**:
    - **[RECOMMENDED]  [Miniconda (v3)](https://www.anaconda.com/docs/getting-started/miniconda/install)**
    - *[arm64/aarch64]  [Miniforge (v3)](https://github.com/conda-forge/miniforge)*
    - *[Python virutal environment]  [venv](https://docs.python.org/3/library/venv.html)*
- Install **PostrgreSQL (>= v16)**:
    - **[RECOMMENDED]  [Docker image](https://hub.docker.com/_/postgres)** (postgres)
    - *[Packages and installers](https://www.postgresql.org/download)*
- Install **libpq (>= v16)** for **psycopg[c]**:
    - **[RECOMMENDED] Miniconda - [libpq](https://anaconda.org/anaconda/libpq)**
    - Debian/Ubuntu - **libpq-dev**
    - MacOS - **[libpq](https://formulae.brew.sh/formula/libpq)**

[OPTIONAL] For **DEVELOPMENT** environment:

- Install [**git**](https://git-scm.com/downloads)
- Setup an [**SSH key**](https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh) ([video tutorial](https://www.youtube.com/watch?v=snCP3c7wXw0))

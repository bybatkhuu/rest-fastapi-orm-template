# ⚙️ Configuration

## 🌎 Environment Variables

[**`.env.example`**](https://github.com/bybatkhuu/rest-fastapi-orm-template/blob/main/.env.example):

```sh
## --- Environment variable --- ##
ENV=LOCAL
DEBUG=false
# TZ=Asia/Seoul


## --- DB configs --- ##
FOT_DB_HOST=localhost
FOT_DB_PORT=5432
FOT_DB_USERNAME=fot_admin
FOT_DB_PASSWORD="FOT_DB_PASSWORD123" # !!! CHANGE THIS TO RANDOM PASSWORD !!!
FOT_DB_DATABASE=fot_db
# FOT_DB_DSN_URL="postgresql+psycopg://fot_admin:FOT_DB_PASSWORD123@localhost:5432/fot_db" # !!! CHANGE THIS TO REAL DSN URL !!!

# FOT_DB_READ_HOST=localhost
# FOT_DB_READ_PORT=5432
# FOT_DB_READ_USERNAME=fot_admin
# FOT_DB_READ_PASSWORD="FOT_DB_PASSWORD123" # !!! CHANGE THIS TO RANDOM PASSWORD !!!
# FOT_DB_READ_DATABASE=fot_db
# FOT_DB_READ_DSN_URL="postgresql+psycopg://fot_admin:FOT_DB_PASSWORD123@localhost:5432/fot_db" # !!! CHANGE THIS TO REAL DSN URL !!!


## -- API configs -- ##
FOT_API_PORT=8000
# FOT_API_LOGS_DIR="/var/log/rest-fastapi-orm-template"
# FOT_API_DATA_DIR="/var/lib/rest-fastapi-orm-template"
# FOT_API_VERSION="1"
# FOT_API_PREFIX="/api/v{api_version}"
# FOT_API_DOCS_ENABLED=true
# FOT_API_DOCS_OPENAPI_URL="{api_prefix}/openapi.json"
# FOT_API_DOCS_DOCS_URL="{api_prefix}/docs"
# FOT_API_DOCS_REDOC_URL="{api_prefix}/redoc"
```

## 🔧 Command arguments

You can customize the command arguments to debug or run the service with different commands.

[**`compose.override.yml`**](https://github.com/bybatkhuu/rest-fastapi-orm-template/blob/main/templates/compose/compose.override.dev.yml):

```yml
    command: ["/bin/bash"]
    command: ["-b", "pwd && ls -al && /bin/bash"]
    command: ["-b", "python -u -m api"]
    command: ["-b", "uvicorn main:app --host=0.0.0.0 --port=${FOT_API_PORT:-8000} --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips='*'"]
```

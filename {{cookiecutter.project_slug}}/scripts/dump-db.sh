#!/usr/bin/env bash
set -euo pipefail


## --- Base --- ##
_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-"$0"}")" >/dev/null 2>&1 && pwd -P)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2


# shellcheck disable=SC1091
[ -f .env ] && . .env


# Checking docker and docker compose installed:
if ! command -v docker >/dev/null 2>&1; then
	echo "[ERROR]: Not found 'docker' command, please install it first!" >&2
	exit 1
fi

if ! docker info > /dev/null 2>&1; then
	echo "[ERROR]: Unable to communicate with the docker daemon. Check docker is running or check your account added to docker group!" >&2
	exit 1
fi

if ! docker compose > /dev/null 2>&1; then
	echo "[ERROR]: 'docker compose' not found or not installed!" >&2
	exit 1
fi

if [ ! -f ./scripts/get-version.sh ]; then
	echo "[ERROR]: 'get-version.sh' script not found!" >&2
	exit 1
fi
## --- Base --- ##


## --- Variables --- ##
BACKUPS_DIR="${BACKUPS_DIR:-./volumes/backups}"
DB_SERVICE_NAME="${DB_SERVICE_NAME:-db}"
## --- Variables --- ##


if ! docker compose ps --services --filter "status=running" | grep -q "^${DB_SERVICE_NAME}$"; then
	echo "[WARN]: '${DB_SERVICE_NAME}' service is not running!" >&2
	exit 1
fi

if [ ! -d "${BACKUPS_DIR}" ]; then
	mkdir -pv "${BACKUPS_DIR}" || exit 2
fi


## --- Main --- ##
main()
{
	echo "[INFO]: Checking current version..."
	_current_version="$(./scripts/get-version.sh)"
	echo "[OK]: Current version: '${_current_version}'"

	echo "[INFO]: Dumping database into dump file..."
	local _dt
	_dt=$(date -u '+%y%m%d-%H%M%S')
	_dump_file_path="${BACKUPS_DIR}/{{cookiecutter.project_abbr}}.db.v${_current_version}.${_dt}.dump"
	echo "[INFO]: Dump file path: '${_dump_file_path}'"

	echo -e "[INFO]: Dumping database...\n"
	docker compose exec -T "${DB_SERVICE_NAME}" pg_dump \
		-p "{% raw %}${{% endraw %}{{cookiecutter.env_prefix}}DB_PORT}" \
		-U "{% raw %}${{% endraw %}{{cookiecutter.env_prefix}}DB_USERNAME}" \
		-d "{% raw %}${{% endraw %}{{cookiecutter.env_prefix}}DB_DATABASE}" \
		-Fc -v \
		-f "/tmp/db.${_dt}.dump" || exit 2
	echo -e "\n[INFO]: Done."

	echo -e "[INFO]: Copying dump file from container to host..."
	docker compose cp "${DB_SERVICE_NAME}:/tmp/db.${_dt}.dump" "${_dump_file_path}" || exit 2
	docker compose exec -T "${DB_SERVICE_NAME}" rm -vrf "/tmp/db.${_dt}.dump" || exit 2
	echo "[OK]: Done."

	echo "[OK]: Successfully dumped database into dump file."
}

main
## --- Main --- ##

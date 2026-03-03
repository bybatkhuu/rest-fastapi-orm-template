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

	echo "[INFO]: Backing up PostgreSQL database..."
	_dump_file_path="${BACKUPS_DIR}/fot.postgres.v${_current_version}.$(date -u '+%y%m%d_%H%M%S').sql.gz"
	echo "[INFO]: Creating backup file: '${_dump_file_path}'"

	docker compose exec -T "${DB_SERVICE_NAME}" \
		env PGPASSWORD="${FOT_DB_PASSWORD}" \
		pg_dump \
			--username="${FOT_DB_USERNAME}" \
			--dbname="${FOT_DB_DATABASE}" \
			--verbose \
			--clean \
			--if-exists \
			--no-owner \
			--no-privileges \
		| gzip > "${_dump_file_path}" || exit 2

	echo "[OK]: Database backup completed."
}

main
## --- Main --- ##

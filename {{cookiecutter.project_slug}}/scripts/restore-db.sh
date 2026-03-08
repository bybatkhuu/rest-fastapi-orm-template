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
## --- Base --- ##


## --- Variables --- ##
BACKUPS_DIR="${BACKUPS_DIR:-./volumes/backups}"
DB_SERVICE_NAME="${DB_SERVICE_NAME:-db}"
## --- Variables --- ##


if ! docker compose ps --services --filter "status=running" | grep -q "^${DB_SERVICE_NAME}$"; then
	echo "[ERROR]: '${DB_SERVICE_NAME}' service is not running!" >&2
	exit 1
fi

if [ ! -d "${BACKUPS_DIR}" ]; then
	echo "[ERROR]: Backups directory '${BACKUPS_DIR}' not found!" >&2
	exit 1
fi


## --- Main --- ##
main()
{
	echo "[INFO]: Searching latest dump file..."
	_dump_file_path="$(find -L "${BACKUPS_DIR}" -type f -name "*.dump" | sort | tail -n 1)"
	if [ -z "${_dump_file_path}" ]; then
		echo "[ERROR]: Not found any dump files in '${BACKUPS_DIR}' directory!" >&2
		exit 1
	fi
	echo "[OK]: Found latest dump file: '${_dump_file_path}'"

	echo "[INFO]: Restoring database from dump file..."
	local _dump_filename
	_dump_filename="$(basename "${_dump_file_path}")"

	echo "[INFO]: Copying dump file into container..."
	docker compose cp "${_dump_file_path}" "${DB_SERVICE_NAME}:/tmp/${_dump_filename}" || exit 2

	echo -e "[INFO]: Restoring database...\n"
	docker compose exec -T "${DB_SERVICE_NAME}" pg_restore \
		-p "{% raw %}${{% endraw %}{{cookiecutter.env_prefix}}DB_PORT}" \
		-U "{% raw %}${{% endraw %}{{cookiecutter.env_prefix}}DB_USERNAME}" \
		-d "{% raw %}${{% endraw %}{{cookiecutter.env_prefix}}DB_DATABASE}" \
		-c --if-exists -v \
		"/tmp/${_dump_filename}" || exit 2
	echo -e "\n[INFO]: Done."

	docker compose exec -T "${DB_SERVICE_NAME}" rm -vrf "/tmp/${_dump_filename}" || exit 2
	echo "[OK]: Successfully restored database from dump file."
}

main
## --- Main --- ##

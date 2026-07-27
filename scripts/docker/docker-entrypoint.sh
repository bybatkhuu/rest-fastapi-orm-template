#!/usr/bin/env bash
set -euo pipefail


echo "[INFO]: Running '${FOT_API_SLUG}' docker-entrypoint.sh..."

_SUDO="sudo"
_GOSU=""
if [ "$(id -u)" -eq 0 ]; then
	_SUDO=""
	_GOSU="gosu ${USER}:${GROUP}"
elif ! command -v sudo >/dev/null 2>&1; then
	echo "[ERROR]: 'sudo' is required when not running as root!" >&2
	exit 1
fi


_run()
{
	echo "[INFO]: Starting alembic migration..."
	${_GOSU} alembic -x data=true upgrade head || exit 2
	echo -e "[OK]: Alembic migration completed successfully.\n"

	echo "[INFO]: Starting FastAPI server..."
	exec ${_GOSU} python -m api || exit 2
	# exec gosu "${USER}:${GROUP}" uvicorn api.main:app \
	# 	--host=0.0.0.0 \
	# 	--port=${FOT_API_PORT:-8000} \
	# 	--no-access-log \
	# 	--no-server-header \
	# 	--proxy-headers \
	# 	--forwarded-allow-ips='*' || exit 2
	exit 0
}


main()
{
	umask 0002 || exit 2

	find "${FOT_HOME_DIR}" \
		"${FOT_API_CONFIGS_DIR}" \
		"${FOT_API_DATA_DIR}" \
		"${FOT_API_LOGS_DIR}" \
		"${FOT_API_TMP_DIR}" \
		\( \
			-type d -name ".git" -o \
			-type d -name ".venv" -o \
			-type d -name "venv" -o \
			-type d -name "env" -o \
			-type d -name "modules" -o \
			-type d -name "volumes" -o \
			-type l -name ".env" \
		\) -prune -o -print0 | \
			xargs -0 ${_SUDO} chown -c "${USER}:${GROUP}" || exit 2

	find "${FOT_API_DIR}" "${FOT_API_CONFIGS_DIR}" "${FOT_API_DATA_DIR}" \
		\( \
			-type d -name ".git" -o \
			-type d -name ".venv" -o \
			-type d -name "venv" -o \
			-type d -name "env" -o \
			-type d -name "scripts" -o \
			-type d -name "modules" -o \
			-type d -name "volumes" \
		 \) -prune -o -type d -exec \
			${_SUDO} chmod 770 {} + || exit 2

	find "${FOT_API_DIR}" "${FOT_API_CONFIGS_DIR}" "${FOT_API_DATA_DIR}" \
		\( \
			-type d -name ".git" -o \
			-type d -name ".venv" -o \
			-type d -name "venv" -o \
			-type d -name "env" -o \
			-type d -name "scripts" -o \
			-type d -name "modules" -o \
			-type d -name "volumes" -o \
			-type l -name ".env" \
		\) -prune -o -type f -exec \
			${_SUDO} chmod 660 {} + || exit 2

	find "${FOT_API_DIR}" "${FOT_API_CONFIGS_DIR}" "${FOT_API_DATA_DIR}" \
		\( \
			-type d -name ".git" -o \
			-type d -name ".venv" -o \
			-type d -name "venv" -o \
			-type d -name "env" -o \
			-type d -name "scripts" -o \
			-type d -name "modules" -o \
			-type d -name "volumes" \
		\) -prune -o -type d -exec \
			${_SUDO} chmod ug+s {} + || exit 2

	find "${FOT_API_LOGS_DIR}" "${FOT_API_TMP_DIR}" -type d -exec ${_SUDO} chmod 775 {} + || exit 2
	find "${FOT_API_LOGS_DIR}" "${FOT_API_TMP_DIR}" -type f -exec ${_SUDO} chmod 664 {} + || exit 2
	find "${FOT_API_LOGS_DIR}" "${FOT_API_TMP_DIR}" -type d -exec ${_SUDO} chmod +s {} + || exit 2

	# echo "${USER} ALL=(ALL) ALL" | ${_SUDO} tee -a "/etc/sudoers.d/${USER}" > /dev/null || exit 2
	echo ""

	## Parsing input:
	case ${1:-} in
		"" | -s | --start | start | --run | run)
			_run;;
			# shift;;
		-b | --bash | bash | /bin/bash)
			shift
			if [ -z "${*:-}" ]; then
				echo "[INFO]: Starting bash..."
				exec ${_GOSU} /bin/bash
			else
				echo "[INFO]: Executing command -> ${*}"
				exec ${_GOSU} /bin/bash -c "$@" || exit 2
			fi
			exit 0;;
		*)
			echo "[ERROR]: Failed to parsing input -> ${*}!" >&2
			echo "[INFO]: USAGE: ${0}  -s, --start, start | -b, --bash, bash, /bin/bash"
			exit 1;;
	esac
}

main "$@"

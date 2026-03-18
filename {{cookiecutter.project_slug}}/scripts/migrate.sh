#!/usr/bin/env bash
set -euo pipefail


## --- Base --- ##
_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-"$0"}")" >/dev/null 2>&1 && pwd -P)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2


# shellcheck disable=SC1091
[ -f .env ] && . .env


if ! command -v alembic >/dev/null 2>&1; then
	echo "[ERROR]: Not found 'alembic' command, please install it first!" >&2
	exit 1
fi

cd ./src || exit 2
## --- Base --- ##


## --- Functions --- ##
_create_revision()
{
	_msg="${1:-New migration.}"
	echo "[INFO]: Creating alembic migration with message: ${_msg}"
	alembic revision --autogenerate -m "${_msg}"
	echo "[OK]: Migration created successfully."
}

_upgrade()
{
	_target="${1:-head}"
	echo "[INFO]: Upgrading database to: ${_target}"
	alembic -x data=true upgrade "${_target}"
	echo "[OK]: Database upgraded to: ${_target}"
}

_downgrade()
{
	_target="${1:--1}"
	echo "[INFO]: Downgrading database to: ${_target}"
	alembic downgrade "${_target}"
	echo "[OK]: Database downgraded to: ${_target}"
}

_show_history()
{
	echo "[INFO]: Showing alembic migration history:"
	alembic history
	echo "[OK]: Done."
}

_show_current()
{
	echo "[INFO]: Current alembic migration:"
	alembic current -v
	echo "[OK]: Done."
}

_check_changes()
{
	echo "[INFO]: Checking alembic migration changes:"
	alembic check
	echo "[OK]: Done."
}

_show_heads()
{
	echo "[INFO]: Showing alembic migration heads:"
	alembic heads
	echo "[OK]: Done."
}
## --- Functions --- ##


## --- Menu arguments --- ##
_usage_help() {
	cat <<EOF
USAGE: ${0} <command> [args...]

COMMANDS:
    create | new | revision | rev
    upgrade | up
    downgrade | down
    history | hist
    current | cur | now
    check | validate
    heads | head

OPTIONS:
    -h, --help    Show this help message.
EOF
}

if [ $# -eq 0 ]; then
	_upgrade
	exit 0
fi

while [ $# -gt 0 ]; do
	case "${1}" in
		create | new | revision | rev)
			shift
			_create_revision "$@"
			exit 0;;
		upgrade | up)
			shift
			_upgrade "$@"
			exit 0;;
		downgrade | down)
			shift
			_downgrade "$@"
			exit 0;;
		history | hist)
			shift
			_show_history
			exit 0;;
		current | cur | now)
			shift
			_show_current
			exit 0;;
		check | validate)
			shift
			_check_changes
			exit 0;;
		heads | head)
			shift
			_show_heads
			exit 0;;
		-h | --help)
			_usage_help
			exit 0;;
		*)
			echo "[ERROR]: Failed to parse argument -> ${1}!" >&2
			_usage_help
			exit 1;;
	esac
done
## --- Menu arguments --- ##

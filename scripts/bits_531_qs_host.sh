#!/bin/bash
# file: bits_531_qs_host.sh
# Manage the bluesky queueserver host processes for bits_531.
#
# Starts/stops BOTH:
#   * the RE Manager (start-re-manager, ZMQ control 60615 / info 60625), and
#   * the bluesky-httpserver REST gateway (:60610) that the finch browser uses.
# Each runs in its own named `screen` session so they come up / go down together.
#
# Process detection uses screen SESSION NAMES (see screen_alive/screen_quit),
# which works on macOS and Linux.  The previous version detected the process via
# /proc/<pid>/cwd, which does not exist on macOS -- so `stop` could never find and
# kill the process there.

SHELL_SCRIPT_NAME=${BASH_SOURCE:-${0}}
SCRIPT_DIR="$(dirname "$(readlink -f "${SHELL_SCRIPT_NAME}")")"
CONFIGS_DIR=$(readlink -f "${SCRIPT_DIR}/../src/bits_531/configs")
QSERVER_DIR=$(readlink -f "${SCRIPT_DIR}/../src/bits_531/qserver")
###-----------------------------
### Change program defaults here

# Instrument configuration YAML (holds TILED_PROFILE_NAME / DATABROKER_CATALOG).
ICONFIG_YML="${CONFIGS_DIR}/iconfig.yml"

# Bluesky queueserver configuration YAML file.
# Defines redis_addr, ZMQ addrs, startup_module: bits_531.startup, keep_re, ...
# "export" is for BITS to identify when QS is running.
export QS_CONFIG_YML="${QSERVER_DIR}/qs-config.yml"

# --- HTTP gateway (bluesky-httpserver) settings ------------------------------
# The finch browser talks REST to this gateway; the RE Manager itself is ZMQ-only.
# All of these may be overridden from the environment (e.g. by finch-stack).
HTTP_HOST="${QSERVER_HTTP_SERVER_HOST:-localhost}"
HTTP_PORT="${QSERVER_HTTP_SERVER_PORT:-60610}"
HTTP_API_KEY="${QSERVER_HTTP_SERVER_SINGLE_USER_API_KEY:-test}"
# CORS: the finch browser origin(s) MUST be allowed or the UI's requests are
# refused.  Default suits local dev; on the beamline export the real origins,
# e.g. QSERVER_HTTP_SERVER_ALLOW_ORIGINS="http://192.168.10.155:5173 http://localhost:5173".
HTTP_ALLOW_ORIGINS="${QSERVER_HTTP_SERVER_ALLOW_ORIGINS:-http://localhost:5173}"
# Where the gateway reaches the RE Manager's ZMQ control port (qs-config: 60615).
HTTP_ZMQ_CONTROL_ADDR="${QSERVER_ZMQ_CONTROL_ADDRESS:-tcp://localhost:60615}"
HTTP_STARTUP_COMMAND="uvicorn bluesky_httpserver.server:app --host ${HTTP_HOST} --port ${HTTP_PORT}"

# Host name (from $hostname) where the queueserver host process runs.
# QS_HOSTNAME=amber.xray.aps.anl.gov  # if a specific host is required
QS_HOSTNAME="$(hostname)"

PROCESS=start-re-manager  # from the conda environment
STARTUP_COMMAND="${PROCESS} --config=${QS_CONFIG_YML} --user-group-permissions=${QSERVER_DIR}/user_group_permissions.yaml --existing-plans-devices=${QSERVER_DIR}/existing_plans_and_devices.yaml"

#--------------------
# internal configuration below

if [ ! -f "$(which "${PROCESS}")" ]; then
    echo "PROCESS '${PROCESS}': file not found. CONDA_PREFIX='${CONDA_PREFIX}'"
    exit 1
fi

if [ -z "$STARTUP_DIR" ] ; then
    # If no startup dir is specified, use the directory with this script
    STARTUP_DIR="${SCRIPT_DIR}"
fi

# Session-name suffix.  Prefer the Tiled profile, then the databroker catalog
# (this is the databroker -> Tiled change kept from the current bits_531 script),
# checking the environment first and falling back to iconfig.yml.
iconfig_get() {  # $1 = key name
    [ -f "${ICONFIG_YML}" ] || return 0
    grep -E "^[[:space:]]*${1}:" "${ICONFIG_YML}" | head -1 | awk '{print $NF}'
}
QS_SUFFIX="${TILED_PROFILE_NAME:-}"
[ -z "${QS_SUFFIX}" ] && QS_SUFFIX="${DATABROKER_CATALOG:-}"
[ -z "${QS_SUFFIX}" ] && QS_SUFFIX="$(iconfig_get TILED_PROFILE_NAME)"
[ -z "${QS_SUFFIX}" ] && QS_SUFFIX="$(iconfig_get DATABROKER_CATALOG)"
QS_SUFFIX="${QS_SUFFIX:-default}"

DEFAULT_SESSION_NAME="bluesky_queueserver-${QS_SUFFIX}"

#--------------------

SELECTION=${1:-usage}
SESSION_NAME=${2:-"${DEFAULT_SESSION_NAME}"}
HTTP_SESSION_NAME="bluesky-httpserver-${QS_SUFFIX}"

# But other management commands will fail if mismatch
if [ "$(hostname)" != "${QS_HOSTNAME}" ]; then
    echo "Must manage queueserver process on ${QS_HOSTNAME}.  This is $(hostname)."
    exit 1
fi

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Portable process management via screen session names (macOS + Linux).

function screen_alive() {  # $1 = screen session name
    screen -ls 2>/dev/null | grep -qE "[0-9]+\.${1}[[:space:]]"
}

function screen_quit() {  # $1 = screen session name
    screen -S "${1}" -X quit >/dev/null 2>&1
}

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function start() {
    if [ ! -f "${CONDA_EXE}" ]; then
        echo "No 'conda' command available."
        exit 1
    fi

    if screen_alive "${SESSION_NAME}"; then
        echo "${SESSION_NAME} is already running"
    else
        echo "Starting ${SESSION_NAME}"
        cd "${STARTUP_DIR}" || exit 1
        # Run the RE Manager inside a detached screen session
        screen -DmS "${SESSION_NAME}" -h 5000 ${STARTUP_COMMAND} &
    fi

    if screen_alive "${HTTP_SESSION_NAME}"; then
        echo "${HTTP_SESSION_NAME} is already running"
    else
        echo "Starting ${HTTP_SESSION_NAME} on ${HTTP_HOST}:${HTTP_PORT}"
        QSERVER_HTTP_SERVER_SINGLE_USER_API_KEY="${HTTP_API_KEY}" \
        QSERVER_HTTP_SERVER_ALLOW_ORIGINS="${HTTP_ALLOW_ORIGINS}" \
        QSERVER_ZMQ_CONTROL_ADDRESS="${HTTP_ZMQ_CONTROL_ADDR}" \
        screen -DmS "${HTTP_SESSION_NAME}" -h 5000 ${HTTP_STARTUP_COMMAND} &
    fi
}

function stop() {
    local found=1
    if screen_alive "${SESSION_NAME}"; then
        echo "Stopping ${SESSION_NAME}"
        screen_quit "${SESSION_NAME}"
        found=0
    fi
    if screen_alive "${HTTP_SESSION_NAME}"; then
        echo "Stopping ${HTTP_SESSION_NAME}"
        screen_quit "${HTTP_SESSION_NAME}"
        found=0
    fi
    if [ "${found}" != "0" ]; then
        echo "${SESSION_NAME} is not running"
    fi
}

function restart() {
    stop
    sleep 0.5  # let the ZMQ/HTTP ports free before restarting
    start
}

function checkup () {
    if ! screen_alive "${SESSION_NAME}"; then
        restart
    fi
}

function console () {
    if screen_alive "${SESSION_NAME}"; then
        echo "Attaching to ${SESSION_NAME} (detach with Ctrl-a d)"
        # -x attaches even if another terminal is already attached
        screen -x "${SESSION_NAME}"
    else
        echo "${SESSION_NAME} is not running"
    fi
}

function run_process() {
    # Diagnostic only: run the RE Manager in the foreground (no screen, no HTTP).
    if screen_alive "${SESSION_NAME}"; then
        echo "${SESSION_NAME} is already running, won't start a new one"
        exit 1
    fi
    cd "${STARTUP_DIR}" || exit 1
    ${STARTUP_COMMAND}
}

function run_http() {
    # Run the bluesky-httpserver REST gateway in the foreground (for a tmux
    # pane).  It talks to the RE Manager over ZMQ; the finch browser talks to it.
    QSERVER_HTTP_SERVER_SINGLE_USER_API_KEY="${HTTP_API_KEY}" \
    QSERVER_HTTP_SERVER_ALLOW_ORIGINS="${HTTP_ALLOW_ORIGINS}" \
    QSERVER_ZMQ_CONTROL_ADDRESS="${HTTP_ZMQ_CONTROL_ADDR}" \
    ${HTTP_STARTUP_COMMAND}
}

function status() {
    if screen_alive "${SESSION_NAME}"; then
        echo "${SESSION_NAME} is running"
    else
        echo "${SESSION_NAME} is not running"
    fi
    if screen_alive "${HTTP_SESSION_NAME}"; then
        echo "${HTTP_SESSION_NAME} is running"
    else
        echo "${HTTP_SESSION_NAME} is not running"
    fi
}

function usage() {
    echo "Usage: $(basename "${SHELL_SCRIPT_NAME}") {start|stop|restart|status|checkup|console|run} [NAME]"
    echo ""
    echo "    Manages BOTH the RE Manager (ZMQ) and the bluesky-httpserver REST"
    echo "    gateway (:${HTTP_PORT}) in named screen sessions."
    echo ""
    echo "    COMMANDS"
    echo "        console   attach to the RE Manager screen session"
    echo "        checkup   restart the RE Manager if it is not running"
    echo "        restart   restart both processes"
    echo "        http      run only the HTTP gateway in the foreground (for a tmux pane)"
    echo "        run       run only the RE Manager in the foreground (tmux pane / diagnostic; no HTTP)"
    echo "        start     start both processes (screen)"
    echo "        status    report whether both processes are running"
    echo "        stop      stop both processes"
    echo ""
    echo "    OPTIONAL TERMS"
    echo "        NAME      RE Manager screen session name (default: ${DEFAULT_SESSION_NAME})"
}

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

case ${SELECTION} in
    start) start ;;
    stop | kill) stop ;;
    restart) restart ;;
    status) status ;;
    checkup) checkup ;;
    console) console ;;
    run) run_process ;;
    http) run_http ;;
    *) usage ;;
esac

# -----------------------------------------------------------------------------
# :author:    BCDA
# :copyright: (c) 2017-2025, UChicago Argonne, LLC
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

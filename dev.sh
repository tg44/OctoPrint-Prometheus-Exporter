#!/bin/sh

set -o errexit   # abort on nonzero exitstatus
set -o nounset   # abort on unbound variable
set -o pipefail  # don't hide errors within pipes

# Setup Python virtualenv if necessary
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
else
    source venv/bin/activate
fi

# Install Octoprint if required
if ! pip show octoprint; then
    pip install "OctoPrint>=1.4.0"
fi

mkdir -p venv/octoprint

OCTOPRINT_ARGS=(
    "-c venv/octoprint/config.yml"
    "-b venv/octoprint/"
)

# Configure octoprint for development
octoprint "${OCTOPRINT_ARGS[@]}" config set --bool server.firstRun false
octoprint "${OCTOPRINT_ARGS[@]}" config set --bool server.onlineCheck.enabled false
octoprint "${OCTOPRINT_ARGS[@]}" config set --bool server.pluginBlacklist.enabled false
octoprint "${OCTOPRINT_ARGS[@]}" config set --bool plugins.tracking.enabled false
octoprint "${OCTOPRINT_ARGS[@]}" user add --admin --password admin admin

# Enable virtual printer
octoprint "${OCTOPRINT_ARGS[@]}" config set --bool plugins.virtual_printer.enabled true

octoprint "${OCTOPRINT_ARGS[@]}" config set --bool serial.autoconnect true
octoprint "${OCTOPRINT_ARGS[@]}" config set --int serial.baudrate 0
octoprint "${OCTOPRINT_ARGS[@]}" config set serial.port VIRTUAL

# Install the plugin
octoprint "${OCTOPRINT_ARGS[@]}" dev plugin:install

octoprint "${OCTOPRINT_ARGS[@]}" serve --debug
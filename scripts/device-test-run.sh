#!/bin/bash
#
# What is this?
# This script will start a basic integration test with no test code.
# It will continue to run until you press any key (as seen below).
# Once it quits, it will perform the integration test cleanup, which
# means that the THING and CERTIFICATE created for it, will be destroyed.
#
# You can use this for quick testing to see an active device running.
# For example if you are testing the web frontend and want to interact
# with an active device, you can run this and then let it cleanup the
# AWS IoT Core entries when complete.
#
# How do I use it?
# $ bash <project-root>/scripts/device-test-run.sh

set -e

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

if [ -z "${BASELINE_INTEGRATION_TEST}" ]; then
  BASELINE_INTEGRATION_TEST=${script_name}
  . "${script_dir}/device-test-integration.sh"
  exit $?
fi

read -n 1 -s -r -p "Press any key to quit..."

echo ""

exit 0
#!/bin/bash
#
# What is this?
# This script tests the device code for handling remote shadow updates.
#
# How do I use it?
# $ bash <project-root>/scripts/device-test-integration-shadows-sample.sh

set -e

shadow_name=sample

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

if [ -z "${BASELINE_INTEGRATION_TEST}" ]; then
  BASELINE_INTEGRATION_TEST=${script_name}
  . "${script_dir}/device-test-integration.sh"
  exit $?
fi

function toolchain_require() { [ -n "$(command -v $1)" ] && return 0 || >&2 echo "$1: not found"; return 1; }
toolchain_require aws
toolchain_require python3
toolchain_require docker

function hex_rand() { python3 -c "import random; print(''.join(random.choices('0123456789abcdef', k=$1)))"; return $?; }

function json_loads() {
  python3 - <<-EOF
		import json
		j = json.loads('''$1''')
		for path in '$2'.split('.'):
		  j = j.get(path)
		  if not j: break
		if j: print(j)
	EOF
	return $?
}

random=$(hex_rand 12)

printf 'Waiting for shadow to complete...'
shadow_status=
shadow_start=$(date +%s)
shadow_timeout=120
while true; do

  if (( $(date +%s) - ${shadow_start} >= ${shadow_timeout} )); then
    printf '\n'
    >&2 echo "Timeout (${thing_timeout}s) while waiting for shadow"
    break
  fi

  # wait until the shadow is received and stored
  if [ -n "$(docker container exec -it ${container} /bin/bash -c "ls /tmp/${app_name}/shadows/${shadow_name} 2> /dev/null" 2> /dev/null)" ]; then

    shadow=$(aws iot-data get-thing-shadow --thing-name ${thing_name} --shadow-name ${shadow_name} /dev/stdout)
    desired=$(json_loads "${shadow}" 'state.desired.random')
    reported=$(json_loads "${shadow}" 'state.reported.random')

    if [ -n "${desired}" ] && [ "${desired}" == "${reported}" ]; then

      if [ "${desired}" != "${random}" ]; then

        aws iot-data update-thing-shadow         \
          --thing-name ${thing_name}             \
          --shadow-name ${shadow_name}           \
          --cli-binary-format raw-in-base64-out  \
          --payload "{
            \"state\": {
              \"desired\": {
                \"random\": \"${random}\"
              }
            }
          }"                                     \
          /dev/null                              \
          &> /dev/null

      else

        printf '\n'
        echo "Shadow update was a success"
        shadow_status=succeeded
        break

      fi

    fi

  fi

  printf .

  sleep 1

done

[ "${shadow_status}" == 'succeeded' ] && exit 0 || exit 1
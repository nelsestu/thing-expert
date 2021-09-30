#!/bin/bash
#
# What is this?
# This script is used for the base of each device integration test. Each test
# will call back to this script to perform device provisioning through Docker, and
# then perform any AWS CLI calls and test validation.
#
# After the test is complete, the THING and CERTIFICATE provisioned will be destroyed.
#
# How do I use it?
# You do not need to call this script directly. It should be called from other tests.

set +e # avoid -e to ensure cleanup happens

if [ -z "${BASELINE_INTEGRATION_TEST}" ]; then
  >&2 echo "Missing event value: BASELINE_INTEGRATION_TEST"
  exit 1
fi

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

root_dir=$(cd "${script_dir}/.." && pwd)
device_dir=${root_dir}/device
build_dir=${root_dir}/.build

function toolchain_require() { [ -n "$(command -v $1)" ] && return 0 || >&2 echo "$1: not found"; return 1; }
toolchain_require aws
toolchain_require python3
toolchain_require docker

function hex_rand() { python3 -c "import random; print(''.join(random.choices('0123456789abcdef', k=$1)))"; return $?; }

function json_load() {
  python3 - <<-EOF
		import json
		with open('$1', 'r') as f:
		  j = json.load(f)
		  for path in '$2'.split('.'):
		    j = j.get(path)
		    if not j: break
		  if j: print(j)
	EOF
	return $?
}

app_name=$(json_load "${root_dir}/config.json" 'app_name')

if [ ! -f "${build_dir}/device/${app_name}/run.sh" ]; then
  >&2 echo 'Please run <project-root>/scripts/device-build.sh before this test'
  exit 1
fi

image_file=$(cd "${build_dir}/device/${app_name}" && ls *.tar.gz)
image_id=$(echo "${image_file}" | sed -n "s/^${app_name}-\([a-z0-9]*\)\.tar\.gz$/\1/p")

echo "Loading image file ${app_name}-${image_id}.tar.gz"
docker image load -i "${build_dir}/device/${app_name}/${app_name}-${image_id}.tar.gz"

echo "Starting container ${app_name}:${image_id}"
container=$(                   \
  docker container run         \
    --detach                   \
    --rm                       \
    --volume /mnt/${app_name}  \
    ${app_name}:${image_id}    \
    2> /dev/null               \
    | cut -c -12               \
)

if [ -z "${container}" ]; then
  >&2 echo 'Unable to start container'
  echo "Unloading image ${image_id}"
  docker image rm --force ${image_id}
  exit 1
fi

echo "Started container ${container}"
printf 'Waiting for provisioning to complete'

thing_id=
thing_id_start=$(date +%s)
thing_timeout=120
while true; do

  printf .

  if (( $(date +%s) - ${thing_id_start} >= ${thing_timeout} )); then
    printf '\n'
    >&2 echo "Timeout (${thing_timeout}s) while waiting for provisioning"
    break
  fi

  if [ -z "$(docker container list --quiet | grep ${container})" ]; then
    printf '\n'
    >&2 echo "Container ${container} disappeared while waiting for provisioning"
    break
  fi

  thing_name=$(docker container exec -it ${container} /bin/bash -c "cat /mnt/${app_name}/aws/thing.id 2> /dev/null" 2> /dev/null)
  if [ -n "${thing_name}" ]; then
    printf '\n'
    break
  fi

  sleep 1

done

if [ -n "${thing_name}" ]; then

  echo "Provisioned THING ${thing_name}"

  ( # run the test in subshell to ensure cleanup happens

    echo "Starting test ${BASELINE_INTEGRATION_TEST}"

    . "${script_dir}/${BASELINE_INTEGRATION_TEST}"

  ) && echo "Test succeeded ($?)" || >&2 echo "Test failed ($?)"

else

  echo 'No THING available, skipping test'

fi

if [ -n "$(docker container list --quiet | grep ${container})" ]; then
  echo 'Shutting down...'
  docker container stop --time 15 ${container} > /dev/null
fi

echo "Unloading image ${image_id}"
docker image rm --force ${image_id}

if [ -n "${thing_name}" ]; then

  function get_thing_principal() { aws iot list-thing-principals --thing-name $1 --output text --query 'principals[0]'; return $?; }
  principal_arn=$(get_thing_principal ${thing_name})
  principal_id=$(echo "${principal_arn}" | sed -n 's|^.*/\([a-z0-9]*\)$|\1|p')

  echo "Detaching PRINCIPAL ${principal_id}"
  aws iot detach-thing-principal --thing-name ${thing_name} --principal ${principal_arn}

  echo "Deactivating PRINCIPAL ${principal_id}"
  aws iot update-certificate --certificate-id ${principal_id} --new-status INACTIVE

  while [ "$(get_thing_principal ${thing_name})" != 'None' ]; do
    sleep 1 # detaching is async, make sure it is complete before trying to delete
  done

  echo "Deleting PRINCIPAL ${principal_id}"
  aws iot delete-certificate --certificate-id ${principal_id}

  echo "Deleting THING ${thing_name}"
  aws iot delete-thing --thing-name ${thing_name}

  log_streams=($(aws logs describe-log-streams --log-group-name "${app_name}/things" --log-stream-name-prefix ${thing_name} --output text --query 'logStreams[*].logStreamName'))
  if (( ${#log_streams[@]} )); then
    for log_stream in "${log_streams[@]}"; do
      echo  "Deleting LOG ${app_name}/things/${log_stream}"
      aws logs delete-log-stream --log-group-name "${app_name}/things" --log-stream-name "${log_stream}"
    done
  fi

fi
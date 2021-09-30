#!/bin/bash
#
# What is this?
# This script tests the device code for handling a job which was created remotely.
#
# How do I use it?
# $ bash <project-root>/scripts/device-test-integration-jobs-sample1.sh

set -e

job_name=sample1

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

thing_arn=$(aws iot describe-thing --thing-name ${thing_name} --output text --query 'thingArn')

job_id=$(hex_rand 16)
echo "Creating JOB ${job_id}"

aws iot create-job                                    \
  --targets "${thing_arn}"                            \
  --job-id ${job_id}                                  \
  --timeout-config '{"inProgressTimeoutInMinutes":2}' \
  --document "{
    \"program\": \"${job_name}\"
  }" > /dev/null

sleep 1

printf 'Waiting for job to complete...[queued]...'
job_status=queued
while [ "${job_status}" == 'queued' ] || [ "${job_status}" == 'in_progress' ]; do
  previous_job_status=${job_status}
  job_status=$(aws iot describe-job-execution              \
    --thing-name ${thing_name}                             \
    --job-id ${job_id}                                     \
    --output text --query 'execution.status' 2> /dev/null  \
    | tr '[:upper:]' '[:lower:]'                           \
  )
  printf .
  [ "${previous_job_status}" != "${job_status}" ] && printf "[${job_status}]"
  sleep 1
done

printf '\n'

echo "Job status finished as '${job_status}'"

echo "Deleting JOB ${job_id}"
aws iot delete-job --force --job-id ${job_id}

[ "${job_status}" == 'succeeded' ] && exit 0 || exit 1
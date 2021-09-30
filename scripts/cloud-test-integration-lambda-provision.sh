#!/bin/bash
#
# What is this?
# This script tests the AWS Lambda code used for device provisioning.
#
# How do I use it?
# $ bash <project-root>/scripts/cloud-test-integration-lambda-provision.sh

set -e

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

root_dir=$(cd "${script_dir}/.." && pwd)

function toolchain_require() { [ -n "$(command -v $1)" ] && return 0 || >&2 echo "$1: not found"; return 1; }
toolchain_require aws
toolchain_require python3
toolchain_require openssl
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
topic_prefix=$(json_load "${root_dir}/config.json" 'topic_prefix')

client_id=$(hex_rand 128)
client_key=$(openssl genrsa -out /dev/stdout 2048 2> /dev/null)
client_csr=$(echo "${client_key}" | openssl req -new -key /dev/stdin -out /dev/stdout -subj "/C=US/CN=${app_name}")

AWS_LAMBDA_EVENT=$(echo "{
  'topic': '\$aws/rules/${topic_prefix}/clients/${client_id}/provision',
  'traceId': '$(uuidgen | tr '[:upper:]' '[:lower:]')',
  'clientId': '${client_id}',
  'principal': '$(hex_rand 64)',
  'csr': '${client_csr//$'\n'/\\n}'
}" | tr '"' "'")

AWS_LAMBDA_TYPE=ingest

. "${script_dir}/cloud-test-integration-lambda.sh"
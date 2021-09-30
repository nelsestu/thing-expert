#!/bin/bash
#
# What is this?
# This script tests the AWS Lambda code used for receiving device logs,
# and inserting into Amazon CloudWatch.
#
# NOTE:
# This test hits REDIS, which may not be accessible unless you are on a VPN to your VPC.
# It REDIS cannot be reached, the test will tell the AWS Lambda to use a mock REDIS class instead.
#
# How do I use it?
# $ bash <project-root>/scripts/cloud-test-integration-lambda-log.sh

set -e

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

root_dir=$(cd "${script_dir}/.." && pwd)

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
topic_prefix=$(json_load "${root_dir}/config.json" 'topic_prefix')

redis_address=$(aws ssm get-parameter --name "/${app_name}/redis-address" --output text --query 'Parameter.Value')
redis_status=$(ping -c1 ${redis_address} &> /dev/null; echo $?)

if (( ${redis_status} )); then
  printf "\nUnable to reach Redis server. VPN may be required. Functionality may fail during test run."
  printf "\nSee https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/accessing-elasticache.html#access-from-outside-aws\n\n"
  USE_MOCK_REDIS=1
fi

#client_id=$(uuidgen | tr '[:upper:]' '[:lower:]')
client_id="00000000-0000-4000-8000-000000000000"

AWS_LAMBDA_EVENT=$(echo "{
  'topic': '\$aws/rules/${topic_prefix}/things/${client_id}/log',
  'traceId': '$(uuidgen | tr '[:upper:]' '[:lower:]')',
  'clientId': '${client_id}',
  'principal': '$(hex_rand 64)',
  'level': 'DEBUG',
  'process': 'main',
  'timestamp': $(date +%s)000,
  'message': 'This is a test message from sent through Docker.'
}" | tr '"' "'")

AWS_LAMBDA_TYPE=ingest

. "${script_dir}/cloud-test-integration-lambda.sh"
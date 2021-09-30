#!/bin/bash
#
# What is this?
# This script tests the AWS Lambda code used for the Amazon API Gateway GET /v1/authenticate request.
#
# How do I use it?
# $ bash <project-root>/scripts/cloud-test-integration-lambda-apis-authenticate-get.sh

set -e

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

root_dir=$(cd "${script_dir}/.." && pwd)
cloud_dir=${root_dir}/cloud
build_dir=${root_dir}/.build

function toolchain_require() { [ -n "$(command -v $1)" ] && return 0 || >&2 echo "$1: not found"; return 1; }
toolchain_require aws
toolchain_require python3
toolchain_require docker

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

web_password=$(aws secretsmanager get-secret-value --secret-id "/${app_name}/web-password" --output text --query 'SecretString' | tr -d '\n' | base64)

AWS_LAMBDA_EVENT=$(echo "{
  'resource': '/v1/authenticate',
  'path': '/v1/authenticate',
  'httpMethod': 'GET',
  'headers': {
    'Authorization': '${web_password}'
  },
  'multiValueHeaders': {
    'Authorization': [
      '${web_password}'
    ]
  },
  'queryStringParameters': null,
  'multiValueQueryStringParameters': null,
  'pathParameters': null,
  'stageVariables': null,
  'requestContext': {
    'resourceId': 'test-invoke-resource-id',
    'resourcePath': '/v1/authenticate',
    'httpMethod': 'GET',
    'extendedRequestId': '',
    'requestTime': '$(date -u +'%d/%b/%Y:%H:%M:%S +0000')',
    'path': '/v1/authenticate',
    'accountId': '000000000000',
    'protocol': 'HTTP/1.1',
    'stage': 'test-invoke-stage',
    'domainPrefix': 'testPrefix',
    'requestTimeEpoch': $(date +%s)000,
    'requestId': '$(uuidgen | tr '[:upper:]' '[:lower:]')',
    'identity': {},
    'domainName': 'testPrefix.testDomainName',
    'apiId': 'xxxxxxxxxx'
  },
  'body': null,
  'isBase64Encoded': false
}" | tr '"' "'")

AWS_LAMBDA_TYPE=apis

. "${script_dir}/cloud-test-integration-lambda.sh"
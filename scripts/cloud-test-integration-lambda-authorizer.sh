#!/bin/bash
#
# What is this?
# This script tests the AWS Lambda code used for the Amazon API Gateway Authorizer.
# The authorizer checks a requests Authorization header for a signed JWT token.
# The JWT issuer and secret are pulled from AWS to generate a valid token for the test.
#
# How do I use it?
# $ bash <project-root>/scripts/cloud-test-integration-lambda-authorizer.sh

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

rm -rf "${build_dir}/test"
mkdir -p "${build_dir}/test"
cd "${build_dir}/test"

python3 -m venv .venv
.venv/bin/pip3 install --quiet --upgrade pip
.venv/bin/pip3 install --quiet --upgrade setuptools
.venv/bin/pip3 install --quiet python-jose==3.2.0

app_name=$(json_load "${root_dir}/config.json" 'app_name')

jwt_issuer=$(aws ssm get-parameter --name "/${app_name}/jwt-issuer" --output text --query 'Parameter.Value')
jwt_secret=$(aws secretsmanager get-secret-value --secret-id "/${app_name}/jwt-secret" --output text --query 'SecretString')

jwt=$(.venv/bin/python3 - <<-EOF
	import time
	from jose import jwt
	iat = int(time.time())
	print(jwt.encode({
	  'sub': '00000000-0000-4000-8000-000000000000',
	  'iss': '${jwt_issuer}',
	  'iat': iat, # issued at
	  'exp': iat + 3600, # expires in 1 hour
	}, key='''${jwt_secret}''', algorithm='HS256'))
EOF)

AWS_LAMBDA_EVENT=$(echo "{
  'type': 'REQUEST',
  'methodArn': 'arn:aws:execute-api:xx-xxxx-1:000000000000:xxxxxxxxxx/ESTestInvoke-stage/GET/',
  'resource': '/',
  'path': '/',
  'httpMethod': 'GET',
  'headers': {
    'Authorization': '${jwt}'
  },
  'multiValueHeaders': {
    'Authorization': [
      '${jwt}'
    ]
  },
  'queryStringParameters': {},
  'multiValueQueryStringParameters': {},
  'pathParameters': {},
  'stageVariables': {},
  'requestContext': {
    'resourceId': 'test-invoke-resource-id',
    'resourcePath': '/',
    'httpMethod': 'GET',
    'extendedRequestId': '',
    'requestTime': '$(date -u +'%d/%b/%Y:%H:%M:%S +0000')',
    'path': '/',
    'accountId': '000000000000',
    'protocol': 'HTTP/1.1',
    'stage': 'test-invoke-stage',
    'domainPrefix': 'testPrefix',
    'requestTimeEpoch': $(date +%s)000,
    'requestId': '$(uuidgen | tr '[:upper:]' '[:lower:]')',
    'identity': {},
    'domainName': 'testPrefix.testDomainName',
    'apiId': 'xxxxxxxxxx'
  }
}" | tr '"' "'")

AWS_LAMBDA_TYPE=authorizer

. "${script_dir}/cloud-test-integration-lambda.sh"
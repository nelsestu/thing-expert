#!/bin/bash
#
# What is this?
# This script will pull values for the deployed Cloud Stack and
# use them when building the static files used for a deployment to S3.
#
# The static files will be under <project-root>/web/build
#
# How do I use it?
# $ bash <project-root>/scripts/web-build.sh

set -e

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

root_dir=$(cd "${script_dir}/.." && pwd)
web_dir=${root_dir}/web
build_dir=${root_dir}/.build

function toolchain_require() { [ -n "$(command -v $1)" ] && return 0 || >&2 echo "$1: not found"; return 1; }
toolchain_require aws
toolchain_require python3
toolchain_require npm

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

cd "${web_dir}"

app_name=$(json_load "${root_dir}/config.json" 'app_name')

apigateway_url=$(aws ssm get-parameter --name "/${app_name}/apigateway-url" --output text --query 'Parameter.Value')
bucket_name=$(aws ssm get-parameter --name "/${app_name}/bucket-name" --output text --query 'Parameter.Value')

npm install

REACT_APP_API_URL="${apigateway_url}" \
npm run build
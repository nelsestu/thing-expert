#!/bin/bash
#
# What is this?
# This script is used for deploying lambda function and layer code zips
# independently of the AWS CDK deployment flow.
#
# How do I use it?
# $ bash <project-root>/scripts/cloud-deploy-lambdas.sh [-type <type>]

set -e

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

lambda_types=

while test $# -gt 0; do
  case "$1" in
    -type) lambda_types=("$2"); shift;;
    *) >&2 echo "Bad argument $1"; exit 1;;
  esac
  shift
done

root_dir=$(cd "${script_dir}/.." && pwd)
cloud_dir=${root_dir}/cloud
build_dir=${root_dir}/.build

if [ -z "${lambda_types}" ]; then
  lambda_types=($(find "${cloud_dir}/cdk/baseline_cdk/resources" -type f -name 'lambda_*.py' | sed -n 's|.*/lambda_\(.*\)\.py|\1|p'))
fi

function toolchain_require() { [ -n "$(command -v $1)" ] && return 0 || >&2 echo "$1: not found"; return 1; }
toolchain_require aws
toolchain_require python3

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

echo "$(

  find "${build_dir}/cloud/deploy" -mindepth 1 | \
    grep -v "${build_dir}/cloud/deploy/.venv"

)" | while read f; do rm -rf "${f}"; done

mkdir -p "${build_dir}/cloud/deploy"
cd "${build_dir}/cloud/deploy"

python3 -m venv .venv
.venv/bin/pip3 install --quiet --upgrade pip
.venv/bin/pip3 install --quiet --upgrade setuptools
.venv/bin/pip3 install --quiet -r "${cloud_dir}/cdk/requirements.txt"

echo "Using lambda types: ${lambda_types[@]}"

for lambda_type in "${lambda_types[@]}"; do

  PYTHONPATH="${cloud_dir}/cdk" \
  .venv/bin/python3 -u -B - <<-EOF

		from baseline_cdk.util import cdk
		cdk.outdir = '$(pwd)'
		cdk.app_name = '${app_name}'
		cdk.topic_prefix = '$(json_load "${root_dir}/config.json" 'topic_prefix')'

		from baseline_cdk.resources import lambda_${lambda_type}

		print('Creating ${app_name}/lambda-${lambda_type}-layer.zip')
		lambda_${lambda_type}.create_layer_zip()

		print('Creating ${app_name}/lambda-${lambda_type}.zip')
		lambda_${lambda_type}.create_lambda_zip()

	EOF

  echo "Uploading ${app_name}/lambda-${lambda_type}-layer.zip"

  layer_version_arn=$(aws lambda publish-layer-version               \
    --layer-name "${app_name}-${lambda_type}"                        \
    --compatible-runtimes "python3.8"                                \
    --zip-file "fileb://${app_name}/lambda-${lambda_type}-layer.zip" \
    --output text                                                    \
    --query 'LayerVersionArn')

  echo "${layer_version_arn}"

  aws lambda update-function-configuration       \
    --function-name "${app_name}-${lambda_type}" \
    --layers "${layer_version_arn}" > /dev/null

  echo "Uploading ${app_name}/lambda-${lambda_type}.zip"

  function_arn=$(aws lambda update-function-code               \
    --function-name "${app_name}-${lambda_type}"               \
    --publish                                                  \
    --zip-file "fileb://${app_name}/lambda-${lambda_type}.zip" \
    --output text                                              \
    --query 'FunctionArn')

  echo "${function_arn}"

done
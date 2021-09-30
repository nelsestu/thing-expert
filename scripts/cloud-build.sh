#!/bin/bash
#
# What is this?
# This script will perform some preliminary work before calling the AWS CDK.
# The AWS CDK will synthesize the Cloud Stack into an AWS CloudFormation template.
#
# This script does not deploy the template. To also deploy, use cloud-deploy.sh
#
# How do I use it?
# $ bash <project-root>/scripts/cloud-build.sh

set -e

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

root_dir=$(cd "${script_dir}/.." && pwd)
cloud_dir=${root_dir}/cloud
build_dir=${root_dir}/.build

function toolchain_require() { [ -n "$(command -v $1)" ] && return 0 || >&2 echo "$1: not found"; return 1; }
toolchain_require python3
toolchain_require cdk # AWS Cloud Development Kit

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

rm -rf "${build_dir}/cloud"
mkdir -p "${build_dir}/cloud"
cd "${build_dir}/cloud"

python3 -m venv .venv
.venv/bin/pip3 install --quiet --upgrade pip
.venv/bin/pip3 install --quiet --upgrade setuptools
.venv/bin/pip3 install --quiet -r "${cloud_dir}/cdk/requirements.txt"

mkdir cdk
cd cdk

# https://docs.aws.amazon.com/cdk/latest/guide/featureflags.html
cat > cdk.json << EOF
{
  "app": "PYTHONPATH='${cloud_dir}/cdk' ${build_dir}/cloud/.venv/bin/python3 -u -B '${cloud_dir}/cdk/baseline_cdk/cdk.py'",
  "output": "${build_dir}/cloud/cdk",
  "context": $(python3 -c "import json; print(json.dumps({
    '@aws-cdk/core:enableStackNameDuplicates': 'true',
    'aws-cdk:enableDiffNoFail': 'true',
    **json.loads('''$(cat "${root_dir}/config.json")''')
  }, indent=4))"),
  "toolkitStackName": "${app_name}-toolkit",
  "toolkitBucketName": "${app_name}-toolkit-$(uuidgen | tr -d '-' | cut -c -12 | tr '[:upper:]' '[:lower:]')"
}
EOF

cdk synth > "${build_dir}/cloud/template.yaml"
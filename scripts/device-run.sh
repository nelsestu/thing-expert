#!/bin/bash
#
# What is this?
# This script will execute the install.sh and run.sh that are generated and
# packaged with each device build. These are the same scripts that will be
# used when a device receives and OTA update.
#
# You can use this for running the latest build locally, while keeping a
# consistent THING entry between runs. To run the device build and cleanup
# the THING and CERTIFICATE after completion, use device-test-run.sh
#
# How do I use it?
# $ bash <project-root>/scripts/device-run.sh

set -e

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

root_dir=$(cd "${script_dir}/.." && pwd)
device_dir=${root_dir}/device
build_dir=${root_dir}/.build

function toolchain_require() { [ -n "$(command -v $1)" ] && return 0 || >&2 echo "$1: not found"; return 1; }
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

if [ ! -d "${build_dir}/device/${app_name}" ]; then
  >&2 echo 'Please run <project-root>/scripts/device-build.sh before this script'
  exit 1
fi

cd "${build_dir}/device/${app_name}"

bash install.sh
bash run.sh
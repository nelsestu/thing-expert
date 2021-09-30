#!/bin/bash
#
# What is this?
# This script will run a local server that you can use for testing.
# The source files will be used from the built static deployment.
# The data APIs will be pulled from the deployed Cloud Stack.
#
# How do I use it?
# $ bash <project-root>/scripts/web-static.sh

set -e

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

root_dir=$(cd "${script_dir}/.." && pwd)
web_dir=${root_dir}/web
build_dir=${root_dir}/.build

function toolchain_require() { [ -n "$(command -v $1)" ] && return 0 || >&2 echo "$1: not found"; return 1; }
toolchain_require npm

. "${script_dir}/web-build.sh"

cd "${web_dir}"

if [ -z "$(npm list -g serve | grep serve)" ]; then
  npm install -g serve
fi

serve -s build
#!/bin/bash
#
# What is this?
# This script will pull values for the deployed Cloud Stack and
# use them when building the static files used for a deployment to S3.
#
# The files will then be synced to the S3 Bucket.
#
# How do I use it?
# $ bash <project-root>/scripts/web-deploy.sh

set -e

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

root_dir=$(cd "${script_dir}/.." && pwd)
web_dir=${root_dir}/web
build_dir=${root_dir}/.build

function toolchain_require() { [ -n "$(command -v $1)" ] && return 0 || >&2 echo "$1: not found"; return 1; }
toolchain_require aws

. "${script_dir}/web-build.sh"

aws s3 sync "${web_dir}/build" s3://${bucket_name}/web

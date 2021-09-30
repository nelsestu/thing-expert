#!/bin/bash

set -e

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

pyver=
output=
requirements=

while test $# -gt 0; do
  case "$1" in
    -pyver) pyver="$2"; shift;;
    -out) output="$2"; shift;;
    -req) requirements="$2"; shift;;
    *) >&2 echo "Bad argument $1"; exit 1;;
  esac
  shift
done

if [ -z "${pyver}" ] || [ -z "${requirements}" ] || [ -z "${output}" ]; then
  >&2 echo "Usage: ${script_name} -pyver <3.8> -req <requirements.txt> -out <dir>"
  exit 1
fi

function toolchain_require() { [ -n "$(command -v $1)" ] && return 0 || >&2 echo "$1: not found"; return 1; }
toolchain_require docker

# ensure absolute path for mounting in docker
mkdir -p "${output}"
output=$(cd "${output}" && pwd)
echo "Saving pip requirements to: ${output}"

requirements_name=$(basename ${requirements})
requirements_dir=$(cd "$(dirname "${requirements}")" && pwd)

docker container run \
  --rm \
  --volume "${requirements_dir}:/mnt/requirements" \
  --volume "${output}:/mnt/output" \
  --user 0 \
  --entrypoint /bin/bash \
  lambci/lambda:build-python${pyver} \
  -c "
    python3 -Im venv .venv --clear &&
    .venv/bin/pip3 install --upgrade pip &&
    .venv/bin/pip3 install --upgrade setuptools &&
    .venv/bin/pip3 install --upgrade wheel &&
    .venv/bin/pip3 install \\
      --upgrade \\
      --force-reinstall \\
      --no-cache-dir \\
      --target '/mnt/output' \\
      -r '/mnt/requirements/${requirements_name}'
  "
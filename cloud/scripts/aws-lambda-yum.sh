#!/bin/bash

set -e

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

package=
output=

while test $# -gt 0; do
  case "$1" in
    -pkg) package="$2"; shift;;
    -out) output="$2"; shift;;
    *) >&2 echo "Bad argument $1"; exit 1;;
  esac
  shift
done

if [ -z "${package}" ] || [ -z "${output}" ]; then
  >&2 echo "Usage: ${script_name} -pkg <openssl> -out <dir>"
  exit 1
fi

function toolchain_require() { [ -n "$(command -v $1)" ] && return 0 || >&2 echo "$1: not found"; return 1; }
toolchain_require docker

# ensure absolute path for mounting in docker
mkdir -p "${output}"
output=$(cd "${output}" && pwd)

docker container run \
  --rm \
  --volume "${output}:/mnt/output" \
  --user 0 \
  -it \
  --entrypoint /bin/bash \
  lambci/lambda:build-python3.8 \
  -c "
    yum install -y yum-utils
    yumdownloader -y ${package}
    name=\$(basename \$(ls ${package}*.rpm) .rpm)
    mkdir \${name}
    cd \${name}
    rpm2cpio ../\${name}.rpm | cpio -div
    mv ../\${name} /mnt/output/${package}
  "
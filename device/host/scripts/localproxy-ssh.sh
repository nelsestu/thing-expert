#!/bin/bash
#
# Usage: pass arguments that you would pass into <localproxy>

set -e

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

root_dir=$(cd "${script_dir}/../../.." && pwd)
bin_dir="${root_dir}/device/container/files/alpine"

function toolchain_require() { [ -n "$(command -v $1)" ] && return 0 || >&2 echo "$1: not found"; return 1; }
toolchain_require docker

localproxy_args="$@"

docker container run --rm -it --publish 127.0.0.1:22:22/tcp --volume "${bin_dir}:/mnt/bin" alpine:3.12 /bin/sh -c "

  ( # suppress output with a subshell

    echo 'http://dl-cdn.alpinelinux.org/alpine/v3.9/main' >> /etc/apk/repositories

    apk update
    apk upgrade
    apk add 'protobuf==3.6.1-r1'

    mkdir ~/.ssh
    chmod 700 ~/.ssh
    echo '$(cat ~/.ssh/id_rsa)' > ~/.ssh/id_rsa
    chmod 700 ~/.ssh/id_rsa

    apk add openssh-client

  ) &> /dev/null

  /mnt/bin/localproxy ${localproxy_args} &
  localproxy_pid=\$!

  sleep 1

  # in case the localproxy_args are not valid, exit without starting ssh
  [ -n \"\$(kill -0 \${localproxy_pid} 2>&1 | grep 'No such process')\" ] && exit 1

  for i in \$(seq 1 10); do
    [ -n \"\$(netstat -tlpn | grep '127.0.0.1:22')\" ] && break
    sleep 1
  done

  ssh localhost
"
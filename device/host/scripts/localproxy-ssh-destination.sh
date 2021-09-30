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

docker container run --rm -it --volume "${bin_dir}:/mnt/bin" alpine:3.12 /bin/sh -c "

  ( # suppress output with a subshell

    echo 'http://dl-cdn.alpinelinux.org/alpine/v3.9/main' >> /etc/apk/repositories

    apk update
    apk upgrade
    apk add 'protobuf==3.6.1-r1'

    mkdir ~/.ssh
    chmod 700 ~/.ssh
    echo '$(cat ~/.ssh/id_rsa.pub)' > ~/.ssh/authorized_keys

    apk add openssh-server
    ssh-keygen -A

    passwd -d \$(whoami)

  ) &> /dev/null

  /mnt/bin/localproxy ${localproxy_args} &
  localproxy_pid=\$!

  sleep 1

  # in case the localproxy_args are not valid, exit without starting sshd
  [ -n \"\$(kill -0 \${localproxy_pid} 2>&1 | grep 'No such process')\" ] && exit 1

  /usr/sbin/sshd -De
"
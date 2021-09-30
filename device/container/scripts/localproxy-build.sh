#!/bin/bash

set -e

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

root_dir=$(cd "${script_dir}/../../.." && pwd)
build_dir=${root_dir}/.build

function toolchain_require() { [ -n "$(command -v $1)" ] && return 0 || >&2 echo "$1: not found"; return 1; }
toolchain_require docker

rm -rf "${build_dir}/localproxy"
mkdir -p "${build_dir}/localproxy"
cd "${build_dir}/localproxy"

docker container run --rm -it --volume "$(pwd):/mnt/output" alpine:3.12 /bin/sh -c "

  echo 'http://dl-cdn.alpinelinux.org/alpine/v3.10/main' >> /etc/apk/repositories
  echo 'http://dl-cdn.alpinelinux.org/alpine/v3.9/main' >> /etc/apk/repositories

  apk update
  apk upgrade

  apk add linux-headers python3 curl wget git g++ make cmake automake autoconf libtool unzip
  apk add 'boost-dev==1.69.0-r4'
  apk add 'boost-static==1.69.0-r4'
  apk add 'protobuf-dev==3.6.1-r1'
  apk add 'openssl==1.1.1g-r0'
  apk add 'openssl-dev==1.1.1g-r0'
  apk add 'catch2==2.12.2-r0'

  git clone https://github.com/aws-samples/aws-iot-securetunneling-localproxy
  cd aws-iot-securetunneling-localproxy
  mkdir build
  cd build
  cmake ../
  make

  # mkdir bin/certs
  # cd bin/certs
  # wget https://www.amazontrust.com/repository/AmazonRootCA1.pem
  # openssl rehash ./

  mv /aws-iot-securetunneling-localproxy/build/bin/* /mnt/output

  /mnt/output/localproxytest
"
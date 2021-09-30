#!/bin/bash
#
# What is this?
# This script will package the device firmware into a Docker image, along
# with all host-side scripts.
#
# The package will be written to <project-root>/.build/device/<app_name>.tar.gz
#
# How do I use it?
# $ bash <project-root>/scripts/device-build.sh

set -e

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

root_dir=$(cd "${script_dir}/.." && pwd)
device_dir=${root_dir}/device
build_dir=${root_dir}/.build

function toolchain_require() { [ -n "$(command -v $1)" ] && return 0 || >&2 echo "$1: not found"; return 1; }
toolchain_require aws
toolchain_require python3
toolchain_require docker

function rewrite() { [ "$(uname)" == 'Darwin' ] && sed -i '' "s|{{$1}}|$2|g" $3 || sed -i "s|{{$1}}|$2|g" $3; return $?; }

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

rm -rf "${build_dir}/device"
mkdir -p "${build_dir}/device"
cd "${build_dir}/device"

app_name=$(json_load "${root_dir}/config.json" 'app_name')
topic_prefix=$(json_load "${root_dir}/config.json" 'topic_prefix')

aws_iot_endpoint=$(aws iot describe-endpoint --endpoint-type 'iot:Data-ATS' --output text --query 'endpointAddress')

certificate_arn=$(aws ssm get-parameter --name "/${app_name}/cert/provisioning" --output text --query 'Parameter.Value')
certificate_id=$(cut -d '/' -f2 <<< ${certificate_arn})
certificate_key=$(aws secretsmanager get-secret-value --secret-id "/${app_name}/key/${certificate_id}" --output text --query 'SecretString')
certificate_crt=$(aws iot describe-certificate --certificate-id "${certificate_id}" --output text --query 'certificateDescription.certificatePem')

mkdir overlay
pushd overlay

  mkdir -p etc/${app_name}
  cp "${device_dir}/container/files/supervisord.conf.template" etc/${app_name}/supervisord.conf
  rewrite app_name ${app_name} etc/${app_name}/supervisord.conf

  mkdir -p opt/${app_name}
  cp "${device_dir}/container/files/mosquitto.sh.template" opt/${app_name}/mosquitto.sh
  rewrite app_name ${app_name} opt/${app_name}/mosquitto.sh

  cp "${device_dir}/container/files/entrypoint.sh.template" opt/${app_name}/entrypoint.sh
  rewrite app_name ${app_name} opt/${app_name}/entrypoint.sh

  mkdir -p usr/bin
  cp "${device_dir}/container/files/alpine/localproxy" usr/bin/localproxy

  cp "${device_dir}/container/files/mosquitto.conf.template" etc/${app_name}/mosquitto.conf.template
  rewrite app_name ${app_name} etc/${app_name}/mosquitto.conf.template
  rewrite topic_prefix ${topic_prefix} etc/${app_name}/mosquitto.conf.template
  rewrite endpoint ${aws_iot_endpoint} etc/${app_name}/mosquitto.conf.template

  mkdir -p etc/${app_name}/aws
  wget https://www.amazontrust.com/repository/AmazonRootCA1.pem -O etc/${app_name}/aws/root.crt
  echo -n "${certificate_crt}" > etc/${app_name}/aws/client.crt
  echo -n "${certificate_key}" > etc/${app_name}/aws/client.key
  echo -n "${aws_iot_endpoint}" > etc/${app_name}/aws/endpoint

  python3 - <<-EOF
		import json
		with open('opt/${app_name}/config.json', 'w') as f:
		  json.dump({
		    **json.loads('''$(cat "${root_dir}/config.json")'''),
		    **json.loads('''$(cat "${device_dir}/container/config.json")''')
		  }, f, indent=4)
	EOF

popd

cp "${device_dir}/container/files/Dockerfile.template" Dockerfile
rewrite app_name ${app_name} Dockerfile
rewrite requirements "$(cat "${device_dir}/container/requirements.txt" | tr "\n" " ")" Dockerfile

mkdir ${app_name}
pushd ${app_name}

  tag_id=$(uuidgen | tr -d '-' | cut -c -12 | tr '[:upper:]' '[:lower:]')

  docker image build \
    --no-cache \
    --file "${build_dir}/device/Dockerfile" \
    --tag ${app_name}:${tag_id} \
    "${root_dir}"

  image_id=$(docker images --format '{{.ID}}' ${app_name}:${tag_id})

  cp "${device_dir}/host/files/pre-install.sh.template" pre-install.sh
  rewrite app_name ${app_name} pre-install.sh
  rewrite image_id ${image_id} pre-install.sh

  cp "${device_dir}/host/files/install.sh.template" install.sh
  rewrite app_name ${app_name} install.sh
  rewrite image_id ${image_id} install.sh

  cp "${device_dir}/host/files/post-install.sh.template" post-install.sh
  rewrite app_name ${app_name} post-install.sh
  rewrite image_id ${image_id} post-install.sh

  cp "${device_dir}/host/files/run.sh.template" run.sh
  rewrite app_name ${app_name} run.sh
  rewrite image_id ${image_id} run.sh

  cp "${device_dir}/host/files/attach.sh.template" attach.sh
  rewrite app_name ${app_name} attach.sh
  rewrite image_id ${image_id} attach.sh

  cp "${device_dir}/host/files/snapshot.sh.template" snapshot.sh
  rewrite app_name ${app_name} snapshot.sh

  docker image tag ${app_name}:${tag_id} ${app_name}:${image_id}
  docker image save ${app_name}:${image_id} | gzip > ${app_name}-${image_id}.tar.gz
  docker image rm --force ${image_id}

  tar cvzf ../${app_name}.tar.gz \
    ${app_name}-${image_id}.tar.gz \
    pre-install.sh \
    install.sh \
    post-install.sh \
    run.sh \
    attach.sh \
    snapshot.sh

popd

# docker load -i .build/device/*.tar.gz
# docker run -it --rm -v /:/host -v $(pwd):/macos iot-baseline:latest
# docker system prune --all
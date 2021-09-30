#!/bin/bash
#
# What is this?
# This script will perform some preliminary work before calling the AWS CDK.
# The AWS CDK will synthesize the Cloud Stack into an AWS CloudFormation template.
# Once synthesized, the template will then be deployed.
#
# To build without deploying, use cloud-build.sh
#
# How do I use it?
# $ bash <project-root>/scripts/cloud-deploy.sh

set -e

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

. "${script_dir}/cloud-build.sh"

cdk bootstrap
cdk deploy --require-approval=never
#!/bin/bash

function json_loads() {
  python3 - <<-EOF
		import json
		j = json.loads('''$1''')
		for path in '$2'.split('.'):
		  j = j.get(path)
		  if not j: break
		if j: print(j)
	EOF
}

lambda_role_arn=$(aws iam get-role --role-name $1 --output text --query 'Role.Arn')

if [ -n "${lambda_role_arn}" ]; then

  session_id=$(uuidgen | tr -d '-' | cut -c -12 | tr '[:upper:]' '[:lower:]')
  lambda_role=$(aws sts assume-role --role-arn ${lambda_role_arn} --role-session-name ${session_id})

  if [ -n "${lambda_role}" ]; then
    export AWS_ACCESS_KEY_ID=$(json_loads "${lambda_role}" 'Credentials.AccessKeyId')
    export AWS_SECRET_ACCESS_KEY=$(json_loads "${lambda_role}" 'Credentials.SecretAccessKey')
    export AWS_SESSION_TOKEN=$(json_loads "${lambda_role}" 'Credentials.SessionToken')
    AWS_ASSUMED_ROLE_ARN=$(json_loads "${lambda_role}" 'AssumedRoleUser.Arn')
  fi

fi
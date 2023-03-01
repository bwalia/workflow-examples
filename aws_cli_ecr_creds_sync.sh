#!/bin/bash

set -x

aws_account_id=$1
aws_access_key_id=$2
aws_secret_access_key=$3
aws_region=$4

docker build -f Dockerfile_ecr_creds_sync -t ecr_creds_sync . --no-cache

docker run \
-e "AWS_ACCOUNT_ID=${aws_account_id}" \
-e "AWS_ACCESS_KEY_ID=${aws_access_key_id}" \
-e "AWS_SECRET_ACCESS_KEY=${aws_secret_access_key}" \
-e "AWS_DEFAULT_REGION=${aws_region}" \
-v "AWS_ACCOUNT_ID=${aws_account_id}" \
-v "AWS_ACCESS_KEY_ID=${aws_access_key_id}" \
-v "AWS_SECRET_ACCESS_KEY=${aws_secret_access_key}" \
-v "AWS_DEFAULT_REGION=${aws_region}" ecr_creds_sync


#!/bin/bash

set -x

aws_account_id=$1
aws_access_key_id=$2
aws_secret_access_key=$3
aws_region=$4

docker build -f Dockerfile_ecr_creds_sync -t ecr_creds_sync . --no-cache

docker run \
-e "aws_account_id=${aws_account_id}" \
-e "aws_access_key_id=${aws_access_key_id}" \
-e "aws_secret_access_key=${aws_secret_access_key}" \
-e "aws_region=${aws_region}" \
-v "aws_account_id=${aws_account_id}" \
-v "aws_access_key_id=${aws_access_key_id}" \
-v "aws_secret_access_key=${aws_secret_access_key}" \
-v "aws_region=${aws_region}" ecr_creds_sync


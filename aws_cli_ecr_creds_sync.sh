#!/bin/bash

set -x

if [ -z "$1" ];
then
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}
else
      AWS_ACCOUNT_ID=$1
fi

if [ -z "$2" ];
then
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
else
      AWS_ACCESS_KEY_ID=$2
fi

if [ -z "$3" ];
then
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
else
      AWS_SECRET_ACCESS_KEY=$3
fi

if [ -z "$4" ];
then
AWS_DEFAULT_REGION=${AWS_REGION}
else
      AWS_DEFAULT_REGION=$4
fi

docker build -f Dockerfile_ecr_creds_sync -t ecr_creds_sync . --no-cache

docker run \
-e AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID}" \
-e AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
-e AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
-e AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION}" \
-v AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID}" \
-v AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
-v AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
-v AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION}" ecr_creds_sync


#!/bin/bash

echo "My Secret: $1"
echo "Cloud provide name: $2"

if [ -z $2 ]; then
  echo "Cloud provider name is not set"
  exit 1
fi

docker build -t terraform_runner .
docker run terraform_runner


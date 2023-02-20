#!/bin/bash

echo "My Secret: $1"
echo "Cloud provide name: $2"

docker build -t terraform_runner .
docker run terraform_runner


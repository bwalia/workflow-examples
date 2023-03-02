#!/bin/bash

set -x

#echo "Deploying AWS ECR reg creds in kubernetes clusters:"
#AWS_PROFILE=default
#ls -latr
#pwd

aws sts get-caller-identity

ACCOUNTID=$(AWS_PROFILE=$AWS_PROFILE aws sts get-caller-identity | jq ".Account" -r)
REGION=eu-west-2
SECRET_NAME=$REGION-ecr-registry
EMAIL=bwalia@tenthmatrix.co.uk

# This token expires every 12 hours
TOKEN=`aws ecr --region=$REGION get-authorization-token --output text \
    --query authorizationData[].authorizationToken | base64 -d | cut -d: -f2`

export KUBECONFIG=$KUBE_CONFIG_DATA_K3S1

kubectl version

kubectl delete secret --ignore-not-found $SECRET_NAME
kubectl create secret docker-registry $SECRET_NAME \
    --docker-server=https://$ACCOUNT.dkr.ecr.$REGION.amazonaws.com \
    --docker-username=AWS \
    --docker-password="$TOKEN" \
    --docker-email="$EMAIL"

export KUBECONFIG=$KUBE_CONFIG_DATA_K3S2

kubectl version

kubectl delete secret --ignore-not-found $SECRET_NAME
kubectl create secret docker-registry $SECRET_NAME \
    --docker-server=https://$ACCOUNT.dkr.ecr.$REGION.amazonaws.com \
    --docker-username=AWS \
    --docker-password="$TOKEN" \
    --docker-email="$EMAIL"

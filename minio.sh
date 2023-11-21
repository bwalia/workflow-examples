#!/bin/bash

export MINIO_ENDPOINT=$MINIO_ENDPOINT
export MINIO_ACCESS_KEY=$MINIO_ACCESS_KEY
export MINIO_SECRET_KEY=$MINIO_SECRET_KEY

mc alias set myminio $MINIO_ENDPOINT $MINIO_ACCESS_KEY $MINIO_SECRET_KEY 


if ! mc ls myminio/uploads; then
    echo "Bucket doesn't exist"
    mc mb myminio/uploads
else
    echo "Bucket already exists."
fi

# List all buckets
mc ls --recursive myminio

# Upload a file to the bucket
mc cp /app/minio.sh myminio/uploads

# List objects in the bucket
mc ls --recursive myminio/uploads

# Remove the uploaded 
mc rm myminio/uploads/minio.sh

# Remove the bucket
mc rb --force myminio/uploads

if ! mc ls myminio/uploads; then
    echo "Bucket removed successfully"
else
    echo "Failed to remove bucket."
fi

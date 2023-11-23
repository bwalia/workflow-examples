#!/bin/bash
export MINIO_ENDPOINT=$MINIO_ENDPOINT
export MINIO_ACCESS_KEY=$MINIO_ACCESS_KEY
export MINIO_SECRET_KEY=$MINIO_SECRET_KEY

mysql -u root -p password webimpetus_int > /app/dump.sql
echo "mc alias set myminio $MINIO_ENDPOINT $MINIO_ACCESS_KEY $MINIO_SECRET_KEY"
mc alias set myminio $MINIO_ENDPOINT $MINIO_ACCESS_KEY $MINIO_SECRET_KEY

if ! mc ls myminio/db-backup; then
    echo "Bucket doesn't exist"
    mc mb myminio/db-backup
else
    echo "Bucket already exists."
fi

# List all buckets
mc ls --recursive myminio/db-backup

# upload the dump to the bucket
mc cp /app/dump.sql myminio/db-backup/webimpetus-int/dump.sql

# List objects in the bucket
mc ls myminio/db-backup

if ! mc ls myminio/db-backup/webimpetus-int/dump.sql; then
    echo "Failed to upload dump.sql"
else
    echo "Successfully uploaded dump.sql."
fi

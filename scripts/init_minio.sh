#!/bin/sh
# Minimal script to create a bucket using mc (MinIO client) if available.
set -e
if ! command -v mc >/dev/null 2>&1; then
  echo "mc (MinIO client) not found; skip interactive bucket init."
  exit 0
fi

mc alias set local http://localhost:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}
mc mb --ignore-existing local/${MINIO_BUCKET_NAME}
echo "Bucket ${MINIO_BUCKET_NAME} ready"

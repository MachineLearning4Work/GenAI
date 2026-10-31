#!/bin/sh
# Minimal script to create a bucket using mc (MinIO client) if available.
set -e
if ! command -v mc >/dev/null 2>&1; then
  echo "mc (MinIO client) not found; skip interactive bucket init."
  exit 0
fi

: "${MINIO_ROOT_USER:?Export MINIO_ROOT_USER before running this script}"
: "${MINIO_ROOT_PASSWORD:?Export MINIO_ROOT_PASSWORD before running this script}"
MINIO_BUCKET_NAME=${MINIO_BUCKET_NAME:-business-plan-bucket}
MINIO_ENDPOINT=${MINIO_ENDPOINT:-localhost:9000}
scheme=http
if [ "${MINIO_SECURE:-false}" = true ]; then scheme=https; fi
mc alias set local "$scheme://$MINIO_ENDPOINT" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc mb --ignore-existing "local/$MINIO_BUCKET_NAME"
echo "Bucket ${MINIO_BUCKET_NAME} ready"

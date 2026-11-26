#!/usr/bin/env bash
set -euo pipefail

# Print the supported shortcuts when the user gives an unknown command.
usage() {
  cat <<'EOF'
Usage:
  ./run.sh build
  ./run.sh versions
  ./run.sh init
  ./run.sh validate
  ./run.sh plan
  ./run.sh apply
  ./run.sh destroy
  ./run.sh shell
EOF
}

case "${1:-}" in
  build)
    # Build the image that contains Python, Terraform, and Terragrunt.
    docker compose build
    ;;
  versions)
    # Confirm that every required tool is available inside the image.
    docker compose run --rm tools terraform version
    docker compose run --rm tools terragrunt --version
    docker compose run --rm tools python3 --version
    ;;
  init|validate|plan|apply|destroy)
    # Run Terraform through Terragrunt from the development environment directory.
    docker compose run --rm tools bash -lc "cd infra/envs/dev && terragrunt $1"
    ;;
  shell)
    # Open an interactive shell for exploration and teaching.
    docker compose run --rm tools bash
    ;;
  *)
    usage
    exit 1
    ;;
esac

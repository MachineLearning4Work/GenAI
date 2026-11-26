# What is Dockerfile.tools and infra/modules/ml_job?

## Dockerfile.tools

This Dockerfile is a self-contained environment used for running Terraform and Terragrunt commands in this project.

Key points:

- Starts from a lightweight Python 3.12 slim base image.
- Installs essential utilities: bash, curl, git, unzip.
- Downloads specific versions of Terraform and Terragrunt binaries from official sources using `curl -fsSL`.
  - Terraform version `1.9.8` is downloaded from HashiCorp's releases.
  - Terragrunt version `0.68.17` is downloaded from the Gruntwork GitHub releases.
- These binaries are installed into `/usr/local/bin` and are made executable.
- Verifies installed versions with `terraform version` and `terragrunt --version`.
- Sets the working directory to `/workspace` where the project files are mounted by Docker Compose.
- Runs an interactive bash shell by default.

Purpose:

The image provides a consistent environment to run Terraform and Terragrunt commands inside Docker, isolating dependencies and avoiding conflicts on the host machine.

---

## infra/modules/ml_job

This Terraform module manages running a machine learning job using local resources and executing a Python script.

Key files:

- **main.tf**: Defines resources and providers.
- **variables.tf**: Declares input variables used by the module.
- **outputs.tf**: Declares outputs returned after Terraform operations.

### Providers

- **local provider** (`hashicorp/local`, version `~> 2.5`): Manages local files and directories.
- **null provider** (`hashicorp/null`): Manages null resources used for triggers and provisioners.

### Key Concepts

- Paths are constructed relative to the project root and the run name (`runs/dev` in your case).
- The module creates:
  - A directory for the ML run output.
  - A local JSON configuration file (`job_config.json`) with parameters like `run_name` and ML model type.
  - Executes a Python ML script (`ml_job.py`) using a null resource with a `local-exec` provisioner.
- The null resource triggers re-run the Python job if the config, script, or data files change, based on SHA256 hashes.
- Outputs provide paths to the generated `metrics.json` and `predictions.csv` files within the run directory.

### Workflow

1. Terraform ensures the output directory exists.
2. Terraform writes the configuration file.
3. Terraform runs the Python ML job with command-line args pointing to data, config, and output directories.
4. After apply, outputs show where results are stored.

---

## Connection

- The Dockerfile.tools image contains Terraform and Terragrunt CLI tools used to run the infrastructure code from the module.
- The module's local provider is used to manage files inside the Docker container workspace.
- The null provider coordinates running the Python ML job from Terraform, triggered by changes to files or config.

---

This setup enables reproducible, containerized infrastructure automation combined with local execution of an ML training job, orchestrated via Terraform and Terragrunt.

---
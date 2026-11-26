terraform {
  # Terraform itself and both providers are downloaded during init.
  required_version = ">= 1.5.0"

  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

provider "local" {}
provider "null" {}

locals {
  # All paths are inside the mounted project directory in the Docker workflow.
  run_dir      = "${var.project_root}/runs/${var.run_name}"
  config_path  = "${local.run_dir}/job_config.json"
  data_path    = "${var.project_root}/data/train.csv"
  script_path  = "${var.project_root}/ml_job.py"
  metrics_path = "${local.run_dir}/metrics.json"
  output_path  = "${local.run_dir}/predictions.csv"
}

resource "null_resource" "run_directory" {
  # Create the output directory before local_file writes the JSON configuration.
  triggers = {
    run_dir = local.run_dir
  }

  provisioner "local-exec" {
    command = format("mkdir -p %q", local.run_dir)
  }
}

resource "local_file" "job_config" {
  # This is the configuration consumed by the Python application.
  filename = local.config_path
  content = jsonencode({
    run_name = var.run_name
    model    = "linear_regression"
  })

  depends_on = [null_resource.run_directory]
}

resource "null_resource" "ml_job" {
  # Hashes make Terraform rerun the job when code, data, or configuration changes.
  triggers = {
    config_hash = sha256(local_file.job_config.content)
    script_hash = filesha256(local.script_path)
    data_hash   = filesha256(local.data_path)
  }

  provisioner "local-exec" {
    # The command runs inside the tools container when Terraform is run through Compose.
    command = format(
      "%s %q --data %q --config %q --output-dir %q",
      var.python_command,
      local.script_path,
      local.data_path,
      local.config_path,
      local.run_dir
    )
  }

  depends_on = [local_file.job_config]
}

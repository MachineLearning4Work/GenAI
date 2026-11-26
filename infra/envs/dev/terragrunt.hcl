terraform {
  # Reuse the shared Terraform module instead of copying its code per environment.
  source = "../../modules/ml_job"
}

inputs = {
  # dev/ -> envs/ -> infra/ -> project root
  # Terragrunt passes these values into the Terraform module.
  project_root   = abspath("${get_terragrunt_dir()}/../../..")
  run_name       = "dev"
  python_command = "python3"
}

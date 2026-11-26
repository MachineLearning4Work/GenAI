Here is the content for the requested Markdown guide file explaining `main.tf`, `outputs.tf`, `variables.tf`, their connection to `terragrunt.hcl`, and a brief on HCL and TF:

```markdown
# Explanation of Terraform Module and Terragrunt Configuration

## What is Terraform (`.tf` files) and HCL?

- **Terraform** is an Infrastructure as Code (IaC) tool used to define and provision infrastructure using a declarative configuration language.
- The configuration files use the extension `.tf`.
- The language used inside `.tf` files is called **HashiCorp Configuration Language (HCL)**.
- HCL is a human-readable structured language designed specifically for Terraform and other HashiCorp tools.
- `.hcl` files (such as `terragrunt.hcl`) are also written in HCL syntax; Terragrunt extends Terraform by wrapping and simplifying multi-environment infrastructure management.

---

## Overview of Terraform Module Files

### `main.tf`

- Defines the core resources and providers used by the module.
- Declares local variables for paths to output directories, config files, data files, scripts, etc.
- Uses the `local` and `null` providers:
  - **local** provider manages local system files and directories.
  - **null** provider defines "null_resource" which triggers actions like running local scripts.
- Key resources:
  - Creates the output directory for ML job runs.
  - Writes a JSON configuration file consumed by the ML Python script.
  - Runs the ML Python job (`ml_job.py`) using a local-exec provisioner, triggered on changes to config, data, or script files.

### `variables.tf`

- Declares inputs (variables) required by the module:
  - `project_root`: Absolute path to the project root directory.
  - `run_name`: Logical name for the ML run to isolate output directories.
  - `python_command`: Executable command to run Python scripts.
- Enables configuration from outside the module.

### `outputs.tf`

- Declares outputs returned by the module after apply:
  - Path to the generated metrics JSON file.
  - Path to the generated predictions CSV file.
  - The logical `run_name` used.
- These outputs can be used by other modules or shown to the user.

---

## Connection with `infra/envs/dev/terragrunt.hcl`

- `terragrunt.hcl` defines environment-specific inputs for the Terraform module.
- It uses an `inputs` block to pass variables like `project_root` and `run_name` to the Terraform module.
- Example:

  ```hcl
  inputs = {
    project_root   = abspath("${get_terragrunt_dir()}/../../..")
    run_name       = "dev"
    python_command = "python3"
  }
  ```

- When you run `terragrunt plan` or `apply` in this environment, Terragrunt reads this file and injects these variables into the Terraform module.
- This is how the Terraform module receives environment-specific configuration dynamically.

---

## Summary

- `.tf` files are Terraform configuration in HCL language describing resources, variables, and outputs.
- `.hcl` files are also HCL-formatted, here used by Terragrunt to wrap Terraform with environment-specific configs.
- `main.tf` defines resources and how the ML job runs.
- `variables.tf` declares configurable inputs.
- `outputs.tf` exposes important outputs.
- `terragrunt.hcl` passes these variable values for a specific environment (like `dev`), connecting and customizing the Terraform infrastructure.

---
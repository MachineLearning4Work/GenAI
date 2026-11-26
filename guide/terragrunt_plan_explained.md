# Understanding `terragrunt plan` --- Terraform MLOps Demo

## 1. What happened?

The command:

``` bash
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt plan'
```

completed the Terraform planning stage successfully.

**Result:**

``` text
Plan: 3 to add, 0 to change, 0 to destroy.
```

This means Terraform proposes creating three resources. It does not mean
they have already been created. `plan` previews changes; `apply`
executes them.

## 2. Break down the command

  ---------------------------------------------------------------------
  Part                               Meaning
  ---------------------------------- ----------------------------------
  `docker compose run`               Starts a one-off container using a
                                     service from the Compose file.

  `--rm`                             Removes that one-off container
                                     when the command finishes.

  `tools`                            The Compose service used to
                                     provide the Terraform/Terragrunt
                                     tools.

  `bash -lc`                         Runs the following command through
                                     a login shell.

  `cd infra/envs/dev`                Changes to the development
                                     environment directory.

  `&&`                               Runs the next command only if the
                                     directory change succeeds.

  `terragrunt plan`                  Asks Terragrunt to prepare and run
                                     Terraform's plan operation.
  ---------------------------------------------------------------------

Terragrunt is being used as a wrapper/orchestration layer for Terraform.
Terraform evaluates the configuration and produces the proposed changes.

## 3. Reading the plan symbols

Terraform uses symbols to show the proposed action:

  Symbol   Meaning
  -------- ---------------------------------
  `+`      Create a resource
  `~`      Update a resource in place
  `-`      Destroy a resource
  `-/+`    Destroy and recreate a resource

Your output shows `+` for all three resources. No `~` or `-` actions
appear.

## 4. The three proposed resources

### Resource 1: `local_file.job_config`

``` text
# local_file.job_config will be created
```

Terraform plans to create a local JSON configuration file.

Important fields from the plan:

``` text
filename = "../../../runs/dev/job_config.json"
```

This is the configured relative path for the file, resolved in the
execution context used by Terraform.

The file content is generated with `jsonencode`:

``` json
{
  "model": "linear_regression",
  "run_name": "dev"
}
```

**What this means:** the demo is preparing a configuration file that
identifies the model as `linear_regression` and the run as `dev`. A
later script or job can read this file to know which model/run
configuration to use.

The plan also displays file permissions:

``` text
directory_permission = "0777"
file_permission      = "0777"
```

These are the permissions configured for the local-file resource. Actual
permission behavior can depend on the operating system and filesystem.
`0777` is very permissive; for a real deployment, use the
least-permissive permissions that meet the application's needs.

The content hashes and resource ID show `known after apply` because
Terraform will calculate or obtain them when it creates the resource.

### Resource 2: `null_resource.ml_job`

``` text
# null_resource.ml_job will be created
```

A `null_resource` does not represent a cloud server, database, or other
physical infrastructure by itself. It is a Terraform resource commonly
used to model an action or dependency, often with provisioners or
triggers.

Your plan shows three triggers:

``` text
config_hash = "..."
data_hash   = "..."
script_hash = "..."
```

These are fingerprints (hashes) of the configuration, data, and script
inputs.

**Why are these useful?**

They allow Terraform to detect changes in the inputs. If a trigger value
changes, Terraform can replace the `null_resource`, which can cause an
associated provisioner or workflow to run again if one is configured.

For this demo, the names suggest that the ML job is tied to: - the job
configuration; - the input dataset; - the ML script.

Important: the plan output alone does not prove that model training will
run. Check the `null_resource.ml_job` definition for `provisioner`
blocks or other execution logic to confirm what actually happens during
`apply`.

### Resource 3: `null_resource.run_directory`

``` text
# null_resource.run_directory will be created
```

This resource has the trigger:

``` text
run_dir = "../../../runs/dev"
```

It represents a tracked Terraform resource associated with the
development run directory.

A `null_resource` does not create a directory automatically just because
its trigger contains a directory path. If the directory is created
during `apply`, that behavior must be implemented in a provisioner or
another resource. Inspect its configuration to verify.

## 5. Understanding the hashes

Your plan contains:

``` text
config_hash = "81a574..."
data_hash   = "d20d1b..."
script_hash = "3861b3..."
```

A hash is a compact fingerprint calculated from input content.

For example:

-   Change the model configuration → the configuration hash may change.
-   Change the training dataset → the data hash may change.
-   Change the Python training script → the script hash may change.

If the hash is used as a Terraform trigger, a changed hash can make
Terraform replace the associated `null_resource`.

This is useful in MLOps because it helps connect infrastructure/job
execution to specific versions of configuration, data, and code.

## 6. Understanding the outputs

At the end, Terraform displays:

``` text
Changes to Outputs:

metrics_path     = "../../../runs/dev/metrics.json"
predictions_path = "../../../runs/dev/predictions.csv"
run_name         = "dev"
```

These are Terraform outputs: values made available to users or other
configurations after the operation.

  ---------------------------------------------------------------------
  Output                             Purpose
  ---------------------------------- ----------------------------------
  `metrics_path`                     Intended location for model
                                     evaluation metrics, such as
                                     accuracy, RMSE, or other scores.

  `predictions_path`                 Intended location for the model's
                                     predictions in CSV format.

  `run_name`                         Identifies this execution as the
                                     development run.
  ---------------------------------------------------------------------

These output paths describe where the demo expects artifacts to be
stored. The plan does not prove that the files already exist or that the
model has run.

## 7. What does `known after apply` mean?

For example:

``` text
id = (known after apply)
```

Terraform cannot provide the final value during planning because the
resource has not yet been created.

After `apply`, Terraform can record the resulting resource ID and
calculated file metadata in its state.

This is normal behavior.

## 8. What does the final summary mean?

``` text
Plan: 3 to add, 0 to change, 0 to destroy.
```

  Action      Count Interpretation
  --------- ------- -------------------------------------
  Add             3 Create three resources
  Change          0 No in-place updates
  Destroy         0 No resources scheduled for deletion

This is a clean initial plan for the resources shown.

## 9. What should you do next?

If you have reviewed the configuration and agree with the proposed
changes, execute:

``` bash
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt apply'
```

Terraform will show the proposed actions and normally ask for
confirmation. Review the plan again and type `yes` only if you approve.

After applying, inspect the expected run directory and outputs. For
example, from the project root in PowerShell:

``` powershell
Get-ChildItem .\runs\dev
```

Check whether `job_config.json`, `metrics.json`, and `predictions.csv`
exist. Their existence depends on the actual resource and job execution
logic; the plan alone does not guarantee all three files will be
produced.

You can also run the plan again:

``` bash
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt plan'
```

If the configuration and state are unchanged, Terraform should generally
report no further changes.

## 10. The overall MLOps workflow

``` text
Terraform / Terragrunt configuration
              |
              v
       terragrunt init
              |
              v
     Initialize providers/modules
              |
              v
      terragrunt validate
              |
              v
     Check configuration syntax
              |
              v
       terragrunt plan
              |
              v
    Preview proposed changes
              |
              v
      terragrunt apply
              |
              v
       Create resources
              |
              v
  Run the configured ML workflow*
              |
              v
   Produce metrics and predictions*
```

`*` Whether the ML workflow runs and produces these files depends on the
actual provisioners/scripts/resources in the project. Terraform's plan
output by itself does not establish that.

## Key takeaway

Your plan is proposing three things:

1.  Prepare a JSON configuration file for the development ML run.
2.  Create a Terraform tracking resource for the ML job, using hashes to
    detect input changes.
3.  Create a Terraform tracking resource associated with the development
    run directory.

It also declares output paths for metrics and predictions.

**Remember:** `plan` is the preview; `apply` is the execution. Always
review the plan before applying changes, especially in production
environments.

------------------------------------------------------------------------

# 11. What is a Terraform provider?

A **provider** is a plugin that allows Terraform to communicate with and
manage a particular platform, service, or system.

Think of Terraform as the project manager and the provider as the
specialist that knows how to perform a particular operation.

## 11.1 Who develops providers?

Providers are developed and maintained by organizations or individuals
and are commonly distributed through the Terraform Registry.

Examples:

  Provider    What it manages
  ----------- --------------------------------------------
  `aws`       Amazon Web Services
  `azurerm`   Microsoft Azure
  `google`    Google Cloud
  `docker`    Docker resources
  `local`     Local files
  `null`      Null resources used in Terraform workflows

## 11.2 Understanding provider, resource type, and resource name

A Terraform resource declaration generally follows this structure:

``` hcl
resource "RESOURCE_TYPE" "LOCAL_NAME" {
  # Configuration
}
```

For example:

``` hcl
resource "local_file" "job_config" {
  filename = "../../../runs/dev/job_config.json"
  content  = jsonencode({
    model    = "linear_regression"
    run_name = "dev"
  })
}
```

The three concepts are different:

  -----------------------------------------------------------------------
  Component               Meaning                 Who defines it?
  ----------------------- ----------------------- -----------------------
  `resource`              Terraform language      Terraform
                          keyword                 

  `local_file`            Resource type           Provider developer
                          implemented by the      
                          Local provider          

  `job_config`            Local resource name     You
                          chosen by the developer 
  -----------------------------------------------------------------------

In `local_file`, the provider name is `local`, and the resource type is
`local_file`.

In your other examples:

  -------------------------------------------------------------------------------------
  Resource address                Provider          Resource type     Local name
  ------------------------------- ----------------- ----------------- -----------------
  `local_file.job_config`         `local`           `local_file`      `job_config`

  `null_resource.ml_job`          `null`            `null_resource`   `ml_job`

  `null_resource.run_directory`   `null`            `null_resource`   `run_directory`
  -------------------------------------------------------------------------------------

The names after the resource type are not Terraform reserved words. You
choose them, subject to Terraform's naming rules.

## 11.3 How do you declare providers?

Providers are usually declared in a file such as `versions.tf` or
`providers.tf`.

Example:

``` hcl
terraform {
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
```

Explanation:

-   `required_providers` tells Terraform which provider plugins the
    configuration requires.
-   `local` and `null` are the local names used to refer to those
    providers in this configuration.
-   `source` identifies the provider's registry address, such as
    `hashicorp/local`.
-   `version` specifies the acceptable provider version range.

The example version constraints are illustrative. Use the versions
actually specified by your project and its lock file.

## 11.4 What happens during `terragrunt init`?

When you run:

``` bash
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt init'
```

Terragrunt prepares the Terraform working directory and invokes
Terraform initialization.

Terraform uses the provider requirements to locate and install the
necessary provider plugins. It also initializes other required
components, such as modules and the backend when configured.

The selected provider versions are recorded in `.terraform.lock.hcl` so
that subsequent initialization can use consistent versions.

## 11.5 How does a provider connect Terraform to a real system?

For example, your project uses the Local provider:

``` hcl
resource "local_file" "job_config" {
  filename = "../../../runs/dev/job_config.json"
  content  = "{\"model\":\"linear_regression\",\"run_name\":\"dev\"}"
}
```

The Local provider implements the operations needed to create and manage
the file.

Similarly:

-   To create an Azure virtual machine, Terraform uses the Azure
    provider (`azurerm`).
-   To create an AWS S3 bucket, Terraform uses the AWS provider (`aws`).
-   To manage Docker resources, Terraform can use the Docker provider
    (`docker`).

Terraform itself does not contain the implementation for every cloud
platform or service. Providers supply that platform-specific
functionality.

## 11.6 Provider versus resource type versus resource name

  --------------------------------------------------------------------------
  Category                Example                    Explanation
  ----------------------- -------------------------- -----------------------
  Terraform language      `resource`, `variable`,    Part of Terraform's
  keyword                 `output`, `locals`         configuration language

  Provider local name     `local`, `null`, `azurerm` Identifies a provider
                                                     in the configuration

  Provider resource type  `local_file`,              A resource
                          `null_resource`,           implementation supplied
                          `azurerm_resource_group`   by a provider

  Resource local name     `job_config`, `ml_job`     A developer-chosen name
                                                     for a resource instance
  --------------------------------------------------------------------------

**Important:** Renaming a resource's local name can change its Terraform
address. Terraform may then interpret it as a different resource and
propose creating a new one and destroying the old one. For an existing
deployment, use a Terraform `moved` block or an appropriate state-move
procedure when renaming resources.

## 11.7 Conceptual architecture

``` text
        Terraform configuration (.tf files)
                       |
                       v
               Terraform engine
                       |
                       v
                Provider plugins
             /         |          \
            v          v           v
         Local       Azure        AWS
         provider    provider     provider
            |          |           |
            v          v           v
       Local files  Azure cloud  AWS services
```

The provider is the bridge between Terraform and the technology it
manages.

## 11.8 Official documentation

-   [Terraform
    Providers](https://developer.hashicorp.com/terraform/language/providers)
-   [Terraform Registry](https://registry.terraform.io/)
-   [Terraform `required_providers`
    block](https://developer.hashicorp.com/terraform/language/providers/requirements)

**Key takeaway:** Terraform defines the desired configuration, providers
implement communication with external platforms and services, resource
types identify what can be managed, and resource names identify the
individual resources in your configuration.

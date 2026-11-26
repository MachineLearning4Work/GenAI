# Terragrunt Workflow Inside Docker Compose

This guide explains what happens when you run the following four commands:

```bash
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt init'

docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt validate'

docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt plan'

docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt apply'
```

These commands represent a common **Infrastructure as Code (IaC)** workflow using Terragrunt and Terraform inside a temporary Docker container.

## 1. Understand the command structure

Consider this command:

```bash
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt init'
```

| Part | Meaning |
|---|---|
| `docker compose` | Uses Docker Compose to run a service defined in the Compose configuration. |
| `run` | Creates and starts a one-off container for the specified service. |
| `--rm` | Removes that container after the command finishes. |
| `tools` | The Compose service name. Its image, volumes, environment variables and other settings are defined in `docker-compose.yml`. |
| `bash` | Starts the Bash shell inside the container. |
| `-l` | Starts Bash as a login shell. |
| `-c` | Tells Bash to execute the command string that follows. |
| `cd infra/envs/dev` | Changes to the development environment directory inside the container. |
| `&&` | Runs the next command only if the preceding command succeeds. |
| `terragrunt init` | Runs Terragrunt's initialization operation. |

**Important:** `docker compose run` does not necessarily build a new image every time. It creates a one-off container from the configured `tools` service image (and may build it if the Compose configuration or command requires that).

`--rm` removes the container, not automatically its named volumes, bind-mounted files, remote state, or cloud resources.

The path `infra/envs/dev` is interpreted inside the container. It must exist there, usually because the project directory is mounted into the container.

## 2. Step 1 — Initialize

```bash
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt init'
```

### Purpose

Initialization prepares the working directory so Terraform can work with the infrastructure configuration.

Depending on your Terragrunt and Terraform versions and configuration, initialization can:

- Read the `terragrunt.hcl` configuration.
- Identify the Terraform or OpenTofu source module.
- Download or prepare the module.
- Initialize the Terraform working directory.
- Download required provider plugins.
- Configure or initialize the backend used for state.
- Create local initialization metadata and cache files.

Example output (illustrative):

```text
Initializing the backend...
Initializing provider plugins...
Terraform has been successfully initialized!
```

### What it does not do

`init` does not normally create or modify your cloud infrastructure. It prepares the tools and working directory for later operations.

## 3. Step 2 — Validate

```bash
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt validate'
```

### Purpose

Validation checks whether the Terraform configuration is syntactically and structurally valid.

For example:

```hcl
resource "azurerm_resource_group" "example" {
  name     = "my-resource-group"
  location = "Canada Central"
}
```

Terraform checks configuration structure, required arguments, references and compatibility with the provider schemas available in the initialized working directory.

Successful output may look like:

```text
Success! The configuration is valid.
```

### What it does not prove

`validate` does not prove that:

- Your Azure credentials are valid or have sufficient permissions.
- The requested cloud resources are available.
- The deployment will succeed.
- The configuration matches the actual infrastructure.

It primarily checks configuration validity; it does not deploy resources.

## 4. Step 3 — Create an execution plan

```bash
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt plan'
```

### Purpose

Planning calculates the changes Terraform would make to bring the managed infrastructure in line with the configuration.

Terraform uses:

1. **Configuration** — what you declare should exist.
2. **State** — Terraform's record of the resources it manages.
3. **Remote infrastructure** — the actual resources, which Terraform may refresh by querying the provider.

Example configuration:

```hcl
resource "azurerm_resource_group" "example" {
  name     = "my-resource-group"
  location = "Canada Central"
}
```

If the resource does not exist and is not already tracked in state, a plan might show:

```text
Terraform will perform the following actions:

  # azurerm_resource_group.example will be created
  + resource "azurerm_resource_group" "example" {
      + name     = "my-resource-group"
      + location = "Canada Central"
    }

Plan: 1 to add, 0 to change, 0 to destroy.
```

### Common plan symbols

| Symbol | Meaning |
|---|---|
| `+` | Create a resource |
| `~` | Update a resource in place |
| `-` | Destroy a resource |
| `-/+` | Destroy and then recreate a resource |

For example:

```text
Plan: 3 to add, 1 to change, 0 to destroy.
```

This means Terraform proposes creating three resources, changing one, and destroying none.

### Does `plan` deploy anything?

No. A normal `plan` previews proposed changes. However, planning can contact cloud APIs to refresh information about existing resources. It can also fail if credentials, permissions, provider access, or configuration are incorrect.

Always inspect the plan, especially any proposed deletions or replacements.

## 5. Step 4 — Apply the changes

```bash
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt apply'
```

### Purpose

Apply executes the infrastructure changes.

Typically, Terraform:

1. Evaluates the configuration.
2. Creates or obtains an execution plan.
3. Displays the proposed changes.
4. Requests confirmation unless approval is configured otherwise.
5. Calls the cloud provider APIs to create, update, or delete resources.
6. Records the resulting resource information in Terraform state.

Example confirmation:

```text
Terraform will perform the following actions:

  + azurerm_resource_group.example

Plan: 1 to add, 0 to change, 0 to destroy.

Do you want to perform these actions?
  Enter a value: yes
```

After approval, output may look like:

```text
azurerm_resource_group.example: Creating...
azurerm_resource_group.example: Creation complete

Apply complete! Resources: 1 added, 0 changed, 0 destroyed.
```

**Warning:** `apply` can create, update, replace, or destroy real infrastructure. Review the proposed plan before approving it. Be particularly careful when a plan includes resource destruction or replacement.

## 6. How the workflow fits together

```text
docker compose run ...
          |
          v
   terragrunt init
   Prepare working directory,
   modules, providers and backend
          |
          v
 terragrunt validate
 Check configuration structure
          |
          v
   terragrunt plan
 Calculate and preview changes
          |
          v
  Review the plan carefully
          |
          v
  terragrunt apply
 Execute approved changes
          |
          v
 Update infrastructure and state
```

In short:

| Command | Main purpose | Normally changes cloud resources? |
|---|---|---|
| `terragrunt init` | Initialize the working directory | No |
| `terragrunt validate` | Check configuration validity | No |
| `terragrunt plan` | Preview infrastructure changes | No |
| `terragrunt apply` | Execute infrastructure changes | **Yes** |

## 7. Understand Terraform state and Docker persistence

Terraform state records the resources Terraform manages and their relationship to the configuration.

A project might contain directories such as:

```text
infra/
└── envs/
    └── dev/
        ├── terragrunt.hcl
        ├── .terraform/
        └── .terragrunt-cache/
```

A local `terraform.tfstate` file may also exist, but its location depends on the backend configuration.

| Item | Purpose |
|---|---|
| `terragrunt.hcl` | Terragrunt configuration for this environment |
| `.terraform/` | Terraform initialization data, including provider-related metadata |
| `.terragrunt-cache/` | Terragrunt's downloaded module and generated working files |
| `terraform.tfstate` | Local Terraform state, if a local backend is used |

### Why `--rm` matters

Each `docker compose run --rm` command uses a one-off container. When it exits, Docker removes that container.

Files written only to the container's writable layer can therefore disappear. Files can survive if they are stored in:

- A bind-mounted host directory.
- A persistent named Docker volume.
- A remote backend, such as an appropriately configured Azure Storage backend.

**Check your `docker-compose.yml` and `terragrunt.hcl`** to understand where the project directory, cache and state are stored. Do not assume state is persistent merely because the project files are mounted.

For shared or production environments, a properly secured remote state backend is generally preferable. State files and plan files can contain sensitive information; protect them accordingly.

## 8. A safer plan-and-apply workflow

For a more controlled deployment, save the plan and apply that exact saved plan:

```bash
# Generate and save a plan
docker compose run --rm tools bash -lc \
  'cd infra/envs/dev && terragrunt plan -out=tfplan'

# Review and apply the saved plan
docker compose run --rm tools bash -lc \
  'cd infra/envs/dev && terragrunt apply tfplan'
```

This requires the saved plan file to remain available between the two container runs. Make sure the relevant working directory is mounted persistently.

If the plan file is written only inside the temporary container, `--rm` will remove it with the container. Also, saved plans can contain sensitive information, so do not commit them to source control or share them casually.

Terragrunt supports passing Terraform arguments through to Terraform, but exact behavior and supported flags can depend on the Terragrunt version. Check the version and command help used by your project.

## 9. Practical checklist

Before deployment:

- [ ] Confirm that `infra/envs/dev` is the intended environment.
- [ ] Confirm that the `tools` service has the expected Terraform, Terragrunt and provider versions.
- [ ] Confirm that required credentials and environment variables are available inside the container.
- [ ] Confirm that the state backend is configured and accessible.
- [ ] Run `init` when required, such as after changing modules, providers or backend configuration.
- [ ] Run `validate` and resolve configuration errors.
- [ ] Run `plan` and inspect all proposed additions, updates, deletions and replacements.
- [ ] Apply only after reviewing and approving the changes.
- [ ] Verify the resulting resources and state.

## 10. Key concept: Terraform versus Terragrunt

- **Terraform** is the infrastructure-as-code engine. It interprets resource configuration, builds plans, communicates with providers and manages state.
- **Terragrunt** is an orchestration and configuration layer around Terraform or OpenTofu. It can help reuse configuration, manage module sources, configure remote state and coordinate multiple environments.

Your command invokes Terragrunt, which in turn runs the relevant Terraform operations.

The `dev` directory identifies the environment configuration being used. A separate `staging` or `production` directory may have different settings and state. Always verify the target environment before running `apply`.

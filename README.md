# Terraform + Terragrunt + a Tiny Machine-Learning Job

This repository is a small example for learning **Terraform**, **Terragrunt**, and infrastructure automation around a simple ML job.

The goal is not to build a production ML platform. The goal is to make the important ideas visible:

1. A Python program is our ML job.
2. Terraform declares the files and command needed to run that job.
3. Terragrunt supplies environment-specific inputs and calls Terraform consistently.
4. `plan` shows what will change before anything changes.
5. `apply` creates the declared local resources and runs the job.
6. `destroy` removes the resources created by Terraform.

The example uses only Python's standard library. You do not need AWS, Azure, Google Cloud, Docker, or a paid account.

For the fully self-contained workflow, Docker Compose is included. It supplies Python, Terraform, Terragrunt, Bash, and the supporting command-line tools inside one reproducible image. Docker itself must still be installed because it is the host runtime for the container.

## A-to-Z learning checklist

This guide is designed to take a complete beginner through the full concept chain:

```text
A  Application code       -> Python ML job
B  Build environment      -> Dockerfile.tools
C  Compose                -> starts the tools container
D  Data                   -> data/train.csv
E  Environment            -> dev Terragrunt configuration
F  Files                  -> Terraform creates job_config.json and runs/
G  Generated artifacts    -> metrics.json and predictions.csv
H  Hash triggers          -> code/data changes rerun the job
I  Infrastructure as code -> Terraform declares the desired resources
J  Jenkins                -> optional workflow automation comparison
K  Kubernetes/cloud       -> future production runtime options
L  Lifecycle              -> init, validate, plan, apply, destroy
M  Modules                -> reusable Terraform code
N  Outputs                -> result paths printed by Terraform
O  Providers              -> local and null provider plugins
P  Plan                   -> preview before changing anything
Q  Quality checks         -> Python compile and validation steps
R  Resources              -> local_file and null_resource
S  State                  -> Terraform's record of managed resources
T  Terragrunt             -> environment inputs and module reuse
U  Variables              -> project_root, run_name, python_command
V  Versioning             -> pinned tool versions in the Docker image
W  Workflow               -> Python -> Terraform -> Terragrunt -> Compose
X  eXecution              -> local-exec runs inside the tools container
Y  YAML                   -> docker-compose.yml service definition
Z  Zero cloud accounts    -> everything runs locally for learning
```

The project intentionally does **not** create a cloud VM or enforce CPU and memory limits in its basic local module. A later Docker lesson can add container limits, and a cloud lesson can select a VM size. The README explains both extensions and the roles of Terraform, Terragrunt, Jenkins, Docker, Kubernetes, and the cloud provider.

---

## What are Terraform and Terragrunt?

### Terraform

Terraform is an **infrastructure-as-code** tool. Instead of manually clicking through a cloud console or typing a long sequence of commands, you describe the desired end state in configuration files.

For example, this project declares:

- a generated JSON configuration file;
- a local output directory;
- a local command that runs the ML job;
- output values that point to the generated results.

Terraform compares the desired configuration with its state and the real world. It then proposes and performs only the necessary changes.

Important Terraform ideas:

| Idea | Meaning |
|---|---|
| Provider | A plugin that lets Terraform manage a system, such as AWS, Azure, Kubernetes, GitHub, or local files. |
| Resource | One thing Terraform manages, such as a bucket, VM, database, file, or command. |
| Variable | An input that makes configuration reusable. |
| Output | A value Terraform prints after an operation. |
| State | Terraform's record of resources it manages. |
| Plan | A preview of proposed changes. |
| Apply | The operation that makes the proposed changes. |
| Destroy | The operation that removes managed resources. |

### Terragrunt

Terragrunt is a thin wrapper around Terraform. It does not replace Terraform. It helps teams keep Terraform code DRY ("Don't Repeat Yourself") and manage multiple environments such as `dev`, `staging`, and `prod`.

Terragrunt is useful for:

- reusing the same Terraform module in several environments;
- keeping environment inputs in separate files;
- configuring remote state consistently;
- managing dependencies between stacks;
- standardizing common Terraform commands.

In this demo, `infra/envs/dev/terragrunt.hcl` points to the reusable module in `infra/modules/ml_job` and supplies the local project path and run name.

A useful mental model is:

```text
Terragrunt configuration
          |
          v
Terraform module + inputs
          |
          v
Terraform provider resources
          |
          v
Generated config + ML job output
```

---

## Why use infrastructure as code?

Without infrastructure as code, a person might manually create directories, write configuration files, start jobs, and try to remember every command. That approach is difficult to repeat and easy to get wrong.

With Terraform and Terragrunt, you get:

- **Repeatability:** run the same configuration again in another environment.
- **Reviewability:** infrastructure changes can be reviewed in Git like application code.
- **Safety:** `terraform plan` previews changes before applying them.
- **Consistency:** environments use the same module and differ only through explicit inputs.
- **Automation:** CI/CD systems can run plan and apply in a predictable way.
- **Dependency tracking:** Terraform understands which resources depend on others.
- **Drift detection:** Terraform can identify differences between declared configuration and reality.
- **Team collaboration:** remote state and locking can be added when a team is ready.

Terraform does not automatically make an architecture good. It makes the architecture explicit and repeatable. Good naming, security, testing, code review, state management, and least privilege are still required.

---

## What this example does

The Python program reads a tiny CSV data set containing house size and price. It trains a one-variable linear regression model using only the Python standard library, calculates mean absolute error, and writes predictions and metrics.

The infrastructure flow is:

1. Terraform creates the `runs/dev/` directory through a local command resource.
2. Terraform creates `runs/dev/job_config.json`.
3. Terraform runs `ml_job.py` with the training data and generated configuration.
4. The Python job writes:
   - `runs/dev/predictions.csv`
   - `runs/dev/metrics.json`
5. Terraform prints the output paths.

This is intentionally simple. A production system would usually submit a job to a managed service, container platform, Kubernetes, or a workflow orchestrator instead of using a local Terraform provisioner.

---

## Repository layout

```text
terraform-terragrunt-ml-demo/
├── README.md
├── ml_job.py
├── data/
│   └── train.csv
└── infra/
    ├── modules/
    │   └── ml_job/
    │       ├── main.tf
    │       ├── variables.tf
    │       └── outputs.tf
    └── envs/
        └── dev/
            └── terragrunt.hcl
```

The `modules/ml_job` directory is reusable Terraform code. The `envs/dev` directory is an environment-specific Terragrunt configuration.

---

## Prerequisites

### Recommended: use the self-contained Docker environment

The repository includes `Dockerfile.tools` and `docker-compose.yml`. The image contains:

- Python 3.12;
- Terraform 1.9.8;
- Terragrunt 0.68.17;
- Bash, Git, curl, unzip, and CA certificates.

With this option, you only need:

- Docker Engine with the Docker Compose plugin, or Docker Desktop;
- internet access during the first image build and Terraform provider download.

You do **not** need to install Python, Terraform, or Terragrunt on your host machine.

Build the image and verify all tools:

```bash
docker compose build
docker compose run --rm tools terraform version
docker compose run --rm tools terragrunt --version
docker compose run --rm tools python3 --version
```

The project directory is mounted into the container at `/workspace`. Terraform state, generated ML output, and source files remain in your project directory on the host.

### Alternative: install tools directly on the host

You may also install Python 3.9 or newer, Terraform 1.5 or newer, and a compatible Terragrunt version directly on your host. This is optional when using Docker Compose.

The first `terraform init` downloads the `hashicorp/local` and `hashicorp/null` providers from the Terraform Registry, so internet access is needed once.

---

## Quick start

From the project root, using Docker Compose:

```bash
docker compose build
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt init'



docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt validate'
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt plan'
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt apply'
```

When Terraform asks for confirmation, type `yes`.

Then inspect the results:

```bash
cat runs/dev/metrics.json
cat runs/dev/predictions.csv
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt output'
```

The expected metrics are deterministic for the included data. You should see a very small error because the sample data follows a simple linear relationship.

To remove the Terraform-managed resources:

```bash
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt destroy'
```

For shorter commands, the repository also includes `run.sh`:

```bash
./run.sh build
./run.sh versions
./run.sh init
./run.sh validate
./run.sh plan
./run.sh apply
./run.sh destroy
```

On Linux and macOS, make the helper executable once with `chmod +x run.sh`. On Windows, use the equivalent `docker compose run` commands above, or run the commands from Git Bash or WSL.

The generated `runs/` directory is ignored by Git. The Python source and input data remain intact.

---

## Learn by running each Terraform step

### 1. Initialize

```bash
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt init'
```

Terragrunt downloads or prepares the Terraform module and Terraform downloads the provider plugin. Initialization does not create the ML output.

### 2. Format

From `infra/envs/dev`:

```bash
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt hclfmt'
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt fmt'
```

`hclfmt` formats Terragrunt files and `fmt` formats Terraform files.

### 3. Validate

```bash
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt validate'
```

Validation checks syntax and internal consistency. It does not prove that an external API will accept every operation.

### 4. Plan

```bash
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt plan'
```

Read the plan carefully. The first plan should show resources to add. A plan is a preview, not a change.

### 5. Apply

```bash
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt apply'
```

Apply creates the configuration and output directory, then invokes the Python job. Terraform records the managed resources in a local state file in the environment directory.

### 6. Inspect state

```bash
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt state list'
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt show'
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt output'
```

State is how Terraform remembers what it manages. Do not edit the state file by hand.

### 7. Change an input

Edit `infra/envs/dev/terragrunt.hcl` and change:

```hcl
run_name = "dev-v2"
```

Then run:

```bash
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt plan'
docker compose run --rm tools bash -lc 'cd infra/envs/dev && terragrunt apply'
```

Terraform should show that the configuration and job execution need to change. This demonstrates declarative reconciliation: you describe the new desired state, and Terraform calculates the actions.

---

## Understanding the Terraform module

### `variables.tf`

Variables make a module reusable. This example accepts:

- `project_root`: the absolute path to the project;
- `run_name`: the logical name of the run;
- `python_command`: the Python executable to use.

### `main.tf`

The module uses the local provider:

- `local_file.job_config` writes a JSON configuration;
- `null_resource.ml_job` runs the Python command when its trigger changes.

The trigger includes hashes of the Python source, input data, and generated configuration. Therefore, changing the model code or data causes the job to run again on the next apply.

The `depends_on` relationship ensures the command runs after the configuration file exists.

### `outputs.tf`

Outputs provide useful values to a human or to another Terraform module. Here they show where the metrics and predictions were written.

### `terragrunt.hcl`

Terragrunt calls the Terraform module and supplies environment-specific values. The same module could be reused by adding `staging/terragrunt.hcl` and `prod/terragrunt.hcl` with different inputs.

---

## Understanding the Python ML job

`ml_job.py` is deliberately dependency-free so the infrastructure lesson is not hidden behind package installation.

The program:

1. reads rows from `data/train.csv`;
2. calculates the slope and intercept for a one-feature linear regression;
3. predicts the target for each row;
4. calculates mean absolute error;
5. writes a predictions CSV and a metrics JSON file.

Run it directly inside the tools container, without Terraform:

```bash
docker compose run --rm tools bash -lc 'printf "{\"run_name\":\"manual-run\",\"model\":\"linear_regression\"}" > /tmp/example-job-config.json && python3 ml_job.py --data data/train.csv --config /tmp/example-job-config.json --output-dir /tmp/example-ml-output'
```

The config file must contain JSON like:

```json
{
  "run_name": "manual-run",
  "model": "linear_regression"
}
```

The direct run is useful for teaching the difference between **application code** and **infrastructure code**. Python contains the ML behavior; Terraform describes how the job is configured and executed.

---

## Terraform versus Terragrunt: when should I use each?

Use Terraform for:

- declaring infrastructure resources;
- defining modules;
- variables, locals, outputs, and dependencies;
- providers and resource lifecycle behavior.

Use Terragrunt when you have multiple Terraform environments or stacks and want to:

- avoid copying the same Terraform module configuration;
- centralize backend configuration;
- pass different inputs to the same module;
- orchestrate dependencies across modules;
- standardize commands for a team.

For a single small Terraform configuration, Terragrunt may add unnecessary complexity. It becomes more valuable as the number of environments and modules grows.

---

## Terraform versus Terragrunt versus Jenkins

These tools are related, but they solve different problems:

```text
Jenkins
  └── Automates the workflow and decides when commands run
        └── Terragrunt
              └── Organizes Terraform environments and inputs
                    └── Terraform
                          └── Creates and changes infrastructure
                                └── Docker, Kubernetes, cloud VM, or other runtime
                                      └── Python ML job
```

### Comparison table

| Tool | Main purpose | Main question | Typical responsibility | CPU and memory behavior |
|---|---|---|---|---|
| **Terraform** | Infrastructure as code | “What infrastructure should exist?” | Create VMs, disks, networks, databases, containers, or Kubernetes resources | Declares VM sizes or container limits; the cloud, Docker, or Kubernetes enforces them |
| **Terragrunt** | Terraform orchestration and reuse | “Which Terraform configuration and environment inputs should be used?” | Reuse the same Terraform module for dev, staging, and production; manage shared settings and dependencies | Does not allocate CPU or memory itself; it passes values to Terraform |
| **Jenkins** | CI/CD and workflow automation | “When should this sequence of commands run?” | Checkout code, run tests, build images, call Terraform, run ML jobs, deploy, and notify | Uses the CPU and memory of its controller or build agent; Docker/Kubernetes limits can be applied to individual jobs |

### Terraform: creates the environment

Terraform can declare a virtual machine size:

```hcl
resource "aws_instance" "ml_machine" {
  ami           = "ami-example"
  instance_type = "t3.medium"
}
```

The cloud provider decides the exact CPU and memory for `t3.medium`. Terraform requests that machine type; Terraform is not the component that schedules individual Python processes.

Terraform can also declare a Docker container limit:

```hcl
resource "docker_container" "ml_job" {
  name  = "simple-ml-job"
  image = "python:3.12-slim"

  cpus   = 1.0
  memory = 512
}
```

In this example, Docker enforces approximately one CPU and 512 MB of memory. Terraform creates the Docker configuration.

### Terragrunt: selects the environment configuration

Terragrunt does not replace Terraform and does not directly manage CPU or memory. It supplies different inputs to the same Terraform module:

```hcl
# infra/envs/dev/terragrunt.hcl
inputs = {
  vm_size = "small"
  cpu     = 1
  memory  = 512
}
```

```hcl
# infra/envs/prod/terragrunt.hcl
inputs = {
  vm_size = "large"
  cpu     = 4
  memory  = 4096
}
```

The module can stay unchanged while Terragrunt selects smaller development resources and larger production resources.

### Jenkins: runs the workflow

Jenkins is a CI/CD server. It can run a sequence such as:

```text
1. Get the latest Git commit
2. Check the Python code
3. Run unit tests
4. Build a Docker image
5. Run terragrunt plan
6. Ask for approval
7. Run terragrunt apply
8. Run or submit the ML job
9. Publish metrics and notify the team
```

A minimal Jenkins pipeline could look like this:

```groovy
pipeline {
    agent any

    stages {
        stage('Test Python') {
            steps {
                sh 'python3 -m py_compile ml_job.py'
            }
        }

        stage('Terraform Plan') {
            steps {
                dir('infra/envs/dev') {
                    sh 'terragrunt init'
                    sh 'terragrunt plan'
                }
            }
        }

        stage('Run ML Job') {
            steps {
                sh "printf '{\"run_name\":\"jenkins-run\",\"model\":\"linear_regression\"}' > /tmp/job.json"
                sh 'python3 ml_job.py --data data/train.csv --config /tmp/job.json --output-dir runs/jenkins'
            }
        }
    }
}
```

Jenkins does not normally decide the size of a VM. It runs on a Jenkins agent, and that agent has the CPU and memory provided by its VM or host. Terraform can create the Jenkins agent with the desired VM size. Jenkins can also run a Docker command with limits, but Docker enforces those limits:

```bash
docker run --cpus=1 --memory=512m simple-ml-image
```

### How they work together

A practical team workflow might be:

```text
Developer pushes code
        |
        v
Jenkins starts a pipeline
        |
        +-- Tests ml_job.py
        +-- Builds the ML container
        +-- Runs terragrunt plan
        +-- Gets approval for infrastructure changes
        +-- Runs terragrunt apply
        |
        v
Terraform creates or updates the VM/container/platform
        |
        v
The ML job runs with the requested CPU and memory
```

The responsibilities are therefore:

- **Python:** contains the ML behavior.
- **Terraform:** declares infrastructure resources and their desired configuration.
- **Terragrunt:** reuses Terraform modules and supplies environment-specific values.
- **Jenkins:** automates the sequence and decides when the sequence runs.
- **Docker, Kubernetes, or a cloud provider:** actually enforces runtime CPU and memory limits.

For this teaching project, the current local Terraform example is intentionally simpler: Terraform creates files and invokes Python directly. It does not create a VM or limit CPU and memory. The natural next lesson is to replace the direct Python command with a Docker container and add `cpus` and `memory` variables.

---

## A realistic production evolution

This demo is local on purpose. A production ML platform might evolve like this:

```text
Terraform/Terragrunt
    |
    +-- object storage bucket for data and models
    +-- IAM roles and policies
    +-- network and private subnets
    +-- container registry
    +-- managed batch or Kubernetes job
    +-- logging, metrics, and alerts
    +-- remote encrypted Terraform state with locking
```

The Python script could then run in a container or managed batch service. Terraform would provision the platform, while a workflow tool such as Airflow, Argo Workflows, GitHub Actions, or a cloud-native scheduler could submit recurring training jobs.

A common separation is:

- Terraform provisions long-lived infrastructure.
- A CI/CD or workflow system runs short-lived ML jobs.
- The ML job writes data and model artifacts to object storage.

Running application workloads from Terraform provisioners is useful for a classroom and small bootstrap tasks, but it is usually not the best production pattern because Terraform is primarily an infrastructure lifecycle tool.

---

## State and team usage

This demo uses local state to avoid requiring a cloud account. Local state is fine for learning but is not ideal for a team.

For a team, consider:

- a remote state backend;
- encryption at rest;
- state locking;
- separate state per environment or stack;
- least-privilege access;
- CI plan checks on pull requests;
- controlled apply permissions;
- secrets stored outside Git and outside plain Terraform variables.

Never commit secrets or state files containing sensitive values to a public repository.

---

## Common troubleshooting

### `terraform: command not found` or `terragrunt: command not found`

Install the missing tool and make sure its installation directory is on `PATH`.

### Provider download fails

Run `terragrunt init` again with internet access. If you are behind a proxy, configure the proxy for your shell and Terraform installation.

### The job does not rerun after changing Python code

Run `terragrunt plan` and confirm that the `null_resource.ml_job` trigger changed. This example hashes the Python source and CSV input. If Terraform believes nothing changed, check that you edited the files referenced by the module.

### A stale output remains after destroy

Terraform manages the generated configuration and directory-creation command, but the Python program may leave files in the output directory. For a clean teaching reset, remove the ignored directory manually:

```bash
rm -rf runs
```

Do not remove a directory in production until you understand whether it contains valuable artifacts.

### Permission errors

Use a writable project directory and verify that `python3` can execute the script directly.

---

## Suggested classroom lesson plan

1. **Explain the problem:** manual infrastructure and repeatability.
2. **Run the Python job directly:** show application behavior.
3. **Read the Terraform module:** identify variables, resources, triggers, and outputs.
4. **Read the Terragrunt file:** identify module source and environment inputs.
5. **Run `init`, `validate`, and `plan`:** emphasize that plan is safe and reviewable.
6. **Run `apply`:** inspect the generated files and metrics.
7. **Change the run name or data:** run plan again and observe reconciliation.
8. **Run `destroy`:** discuss lifecycle and state.
9. **Discuss production differences:** remote state, cloud resources, secrets, CI/CD, and job orchestration.

A good exercise is to add a second environment:

```text
infra/envs/staging/terragrunt.hcl
```

Point it at the same module, change `run_name`, and run it from that directory. This demonstrates why Terragrunt can be helpful: one module, multiple environment configurations.

---

## License and learning note

This repository is a teaching example. Review and adapt every resource before using similar patterns in production, especially local-exec provisioners, state configuration, credentials, network rules, and data handling.

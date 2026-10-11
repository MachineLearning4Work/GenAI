# Project Proposal: Local CrewAI Business-Plan Pipeline with Jenkins

## Platform and Deployment Preconditions (Important)

**This project assumes:**

- You are running **Windows** with **Docker Desktop** already installed and running.
- **Jenkins and MinIO will ONLY be deployed as Docker containers via Docker Compose.**
- **No manual Jenkins or MinIO installation is required or supported. All core services run exclusively in containers managed by Docker Compose.**

**Key explicit requirements:**

- You will start services (Jenkins, MinIO, CrewAI app) together using Docker Compose. Example: `docker compose up --build`.
- Jenkins will be provisioned from the official Jenkins Docker image within the Compose stack.
- Jenkins will be accessible at [http://localhost:8080](http://localhost:8080) (or the mapped port you specify).
- Jenkins service in Docker Compose will mount the Docker socket for in-container Docker control: `//var/run/docker.sock:/var/run/docker.sock` (with syntax adjusted for Windows if needed).
- Jenkins persistent data is stored in a Docker volume mounted at `/var/jenkins_home`.
- Do **not** attempt to install Jenkins or MinIO manually.
- All file/volume mappings in Compose must support Windows paths and Docker Desktop conventions.

## 1. Project summary

Build a local learning project that accepts a business idea in natural language and uses three CrewAI tasks and ONLY one agent to draft and review a practical business proposal. The single agent is reused for all three tasks; each task's own description and expected output define the job to perform. Each task completes one job (TASK), returns data matching a Pydantic model, and saves its own validated JSON file. The workflow passes earlier task results forward as context so later task can build on them.

GitHub stores the version-controlled source code. A local Docker Compose stack runs the app and MinIO, and the project is designed so a push to a branch such as `docker_compose` can trigger a rebuild. Jenkins or GitHub Actions can automate the build; the first version can use branch-triggered Compose builds on a local machine without requiring public webhook exposure.

MinIO is part of the first working architecture, not an optional add-on. It stores per-run task outputs and model artifacts in a structured bucket layout. MLflow remains optional for run metadata, but MinIO is the required artifact store for the project. CrewAI performs the business-plan work; Docker Compose and CI automation provide the local runtime and build workflow.

## 2. Example user experience

The user enters an idea such as:

> I want to launch an affordable, practical machine-learning course in Montreal for working professionals who want to use ML in their jobs. It should be useful at work and not too expensive.

The program turns that input into three linked analyses:

1. Identify target customers, their needs, market assumptions, and research questions.
2. Propose a course offer, positioning, pricing hypotheses, and customer-acquisition approach, using task 1's findings as context.
3. Review the overall plan for feasibility, risks, missing evidence, and next steps, using tasks 1 and 2 as context.

The result is three validated JSON files plus a combined human-readable Markdown business-plan report. The agent is generating hypotheses, not conducting verified market research; the report must label unsupported claims and recommend validation steps.

## 3. What each component does

| Component | Responsibility | Needed in the first version? |
|---|---|---|
| Python | Runs the application and pipeline code. | Yes |
| Docker Compose | Starts the app, MinIO, and supporting services with local environment variables. | Yes |
| CrewAI | Coordinates the single agent and its three sequential tasks. | Yes |
| Pydantic | Defines and validates the structured result expected from each task. | Yes |
| Git | Tracks changes to source code and configuration. | Yes |
| GitHub Free personal repository | Hosts the source repository and provides change history. | Yes |
| Jenkins | Checks out the repository, runs tests, launches the pipeline, and records build results. | Yes, or GitHub Actions can be used instead |
| Model-provider API | Supplies the language model used by the agent. Its usage may have separate costs. | Yes, unless using a supported local model |
| MinIO | Stores per-run JSON outputs and model artifacts in a local S3-compatible object store. | Yes |
| MLflow | Tracks each run's parameters, tags, status, and artifacts for comparison. | Optional extension |
| FastAPI | Could expose a prompt-submission API or small user interface. | Optional later extension |

Jenkins is the automation system—not the webhook itself, not the AI model, and not the artifact database. A webhook is a notification that can ask Jenkins to start a job. Jenkins can also start through a manual button or repository polling.

## 4. One agent, three tasks, and output files

The initial design uses a **sequential CrewAI process** with a **single reusable agent**. Each task has a Pydantic output model and a JSON output file. The next task receives the earlier structured result as context.

### The single agent

**Agent:** Business Analysis Generalist

**Role:** One CrewAI `Agent` instance performs all three tasks. Its role, goal, and backstory are written broadly enough to cover market research, strategy, and critical review, so the task-specific instructions — not separate agents — determine what each step produces.

**Goal:** Turn a business idea into structured, clearly labelled hypotheses and an honest critique, never presenting unverified claims as facts.

**Why one agent:** It keeps the project small, avoids duplicated configuration, and makes the learning focus the task definitions, structured output, and context hand-off rather than multi-agent orchestration.

### Task 1 — Market and customer discovery

**Task focus:** Market and customer discovery.

**Goal:** Translate the idea into a focused customer and market hypothesis, without presenting unverified claims as facts.

**Output file:** `outputs/01_market_research.json`

**Proposed schema fields:**

- `idea_summary`
- `target_segments` — segment name, characteristics, needs, and possible barriers
- `customer_pain_points`
- `market_assumptions` — each clearly marked as an assumption
- `alternatives_and_competitors` — based only on supplied information unless browsing is later added
- `validation_questions`
- `recommended_research_actions`
- `confidence_notes`

**Context passed forward:** The serialized market-research result becomes context for task 2.

### Task 2 — Business strategy and offer

**Task focus:** Business strategy and offer design.

**Goal:** Develop a focused business concept that addresses the customer needs and assumptions identified in task 1.

**Output file:** `outputs/02_business_strategy.json`

**Proposed schema fields:**

- `positioning_statement`
- `value_proposition`
- `course_offer` — delivery format, outline, duration, and learner outcome hypotheses
- `pricing_hypotheses` — proposed price ranges with rationale, explicitly marked for testing
- `go_to_market_plan` — initial channels and launch experiments
- `revenue_model`
- `key_resources_and_cost_categories`
- `success_metrics`
- `dependencies_and_assumptions`

**Context passed forward:** The serialized market research and business strategy become context for task 3.

### Task 3 — Independent business-plan review

**Task focus:** Independent plan review.

**Goal:** Critique the proposed plan, identify unsupported reasoning, and recommend an achievable next step.

**Output file:** `outputs/03_business_plan_review.json`

**Proposed schema fields:**

- `overall_assessment`
- `strengths`
- `critical_risks` — severity, explanation, and mitigation
- `unsupported_or_missing_evidence`
- `consistency_checks`
- `recommended_experiments`
- `30_day_action_plan`
- `decision` — for example, `proceed_to_validation`, `revise`, or `pause`

**Context passed forward:** The report-generation step uses the three validated objects to assemble the final Markdown proposal. This can be a deterministic Python rendering step rather than a fourth AI task.

The JSON files should be per-run outputs and should not be overwritten across runs. A run identifier, such as a timestamp plus short random suffix, keeps each run separate. The local filesystem keeps the files first, and then the project uploads them to MinIO for artifact storage:

```text
runs/<run_id>/01_market_research.json
runs/<run_id>/02_business_strategy.json
runs/<run_id>/03_business_plan_review.json
runs/<run_id>/business_plan.md
```

MinIO bucket structure:

```text
business-plan-bucket/
├── model/
│   └── trained_model/
│       ├── model.bin
│       ├── metadata.json
│       └── config.yaml
├── task_out/
│   └── <run_id>/
│       ├── 01_market_research.json
│       ├── 02_business_strategy.json
│       ├── 03_business_plan_review.json
│       └── business_plan.md
```

## 5. Proposed architecture and data flow

```text
User enters business idea
          |
          v
Python application validates input
          |
          v
CrewAI Task 1: customer and market hypotheses
          |  Pydantic validation -> local JSON file 1
          v
CrewAI Task 2: business strategy (uses task 1 context)
          |  Pydantic validation -> local JSON file 2
          v
CrewAI Task 3: reviewer (uses tasks 1 and 2 context)
          |  Pydantic validation -> local JSON file 3
          v
Python renders final Markdown report
          |
          +--> local run folder (runs/<run_id>/)
          |
          +--> MinIO artifact upload
          |      +--> bucket/task_out/<run_id>/01_market_research.json
          |      +--> bucket/task_out/<run_id>/02_business_strategy.json
          |      +--> bucket/task_out/<run_id>/03_business_plan_review.json
          |      +--> bucket/task_out/<run_id>/business_plan.md
          |
          +--> MLflow metadata tracking (optional extension)
```

Docker Compose sits around this application as the local runtime layer:

```text
Developer pushes to GitHub branch such as docker_compose
          |
          v
GitHub triggers workflow / Jenkins job
          |
          v
Cleanup old containers and images for this project
          |
          v
docker compose --env-file .env up --build -d
          |
          v
App starts with env-configured ports & credentials
          |
          v
MinIO starts, creates bucket/folders, and stores artifacts
          |
          v
Tests run and build status is reported
```

A key distinction: **changing application code or a committed default prompt can trigger the build pipeline**. An ordinary user submitting a new business idea should run the application directly (or through a future FastAPI interface); it should not require Jenkins or Docker Compose to redeploy or restart for every prompt.

## 6. Jenkins and GitHub plan

### Local mode: recommended starting point

**Jenkins in Docker (not manual install!):**

- Jenkins must run as a Docker container from the official Jenkins image. This is managed entirely via Docker Compose. There is no scenario where Jenkins is installed directly on Windows or run outside of Docker for this project.
- When starting Jenkins for the first time, access the web UI at `localhost:8080`, retrieve the initial admin password from the Jenkins data volume/log, and perform the unlock/admin setup in your browser. Install recommended plugins and create the pipeline job linking to your repo.

- Docker Compose service declaration for Jenkins must include (adjust for platform specifics):
    - Jenkins image (e.g., `jenkins/jenkins:lts`)
    - `//var/run/docker.sock:/var/run/docker.sock` volume for Docker-in-Docker control
    - `jenkins_home` Docker volume for persistence
    - Published port (typically 8080)

Run Jenkins on the learner's own computer or use GitHub Actions for branch-triggered automation. The project is designed so that a push to a branch such as `docker_compose` triggers a rebuild of the local stack. Before building, the pipeline removes older containers and images with the same project name so the new build starts cleanly.

The build flow can include:

1. Check out the selected branch and commit.
2. Create/use a Python virtual environment and install pinned dependencies.
3. Copy `.env.example` to `.env` if needed and read environment variables for ports and secrets.
4. Run cleanup of the project-specific Docker resources (`docker compose down`, image removal, prune).
5. Run formatting or static checks if included.
6. Run unit tests for the Pydantic models and report rendering.
7. Run a small pipeline smoke test, if configured with a test-mode/mock model.
8. Run a live CrewAI generation only when intentionally enabled and configured with a model API key.
9. Verify each JSON file against its Pydantic schema.
10. Upload the JSON files and Markdown report to MinIO under `task_out/<run_id>/`.
11. Mark the build successful or failed and show logs explaining which step failed.

This is useful even if the AI generation is not run on every code change. A sensible default CI behavior is to run tests and a mocked smoke test on every detected change; a user can manually trigger the live model call to control cost and avoid generating a new plan unnecessarily.

### Branch-triggered Docker Compose workflow

**Note:** All CI/CD and local workflow orchestration is performed within containerized services. There is never a requirement to install Jenkins, MinIO, or the pipeline app directly to Windows—always use Docker Compose.

The project should use environment variables for all ports and settings, for example:

- `APP_PORT`
- `MINIO_PORT`
- `MINIO_CONSOLE_PORT`
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`
- `MINIO_BUCKET_NAME`
- `COMPOSE_PROJECT_NAME`

This makes the system portable and keeps deployment configuration out of code. A push to the `docker_compose` branch can trigger a rebuild by running `docker compose --env-file .env up --build -d` after the cleanup step. Doing this on a branch instead of every user prompt avoids unnecessary rebuilds while still supporting automated testing for project changes.

### Optional webhook mode

**Note:** If a webhook is required for remote triggering (optional only!), use a relay/tunnel service (such as ngrok) since Docker Desktop does not make local ports public by default. However, for default local learning, triggering Jenkins manually or by branch push is recommended and does not require any external access.

A webhook is GitHub's event message saying that a push occurred. Jenkins can receive it and start the configured job. But a local Jenkins server at `localhost` is not reachable by GitHub. GitHub's documentation explicitly says that `localhost` and `127.0.0.1` cannot be webhook payload URLs.[1]

To learn webhook delivery while keeping Jenkins on the local machine, use a webhook forwarding relay or a secure tunnel and configure GitHub with its reachable URL. This is an optional learning step, not required for the pipeline. Protect Jenkins with authentication, use a webhook secret where supported, expose only what is needed, and stop the relay when finished. A public server with proper access controls is another option, but it is not needed for this local learning project.

### GitHub Free considerations

**Tip:** Your `.devcontainer` or Compose service files may require small adjustments for Windows path compatibility if you relocate the project.

A personal GitHub Free account includes unlimited public and private repositories.[2] Jenkins itself is open-source software. The model-provider API can incur separate costs depending on provider and usage. The project should use a private repository by default if prompts, configuration, or business materials are sensitive, and should never commit API keys.

## 7. Where MLflow and MinIO fit

The first version should save outputs in both local run folders and MinIO. The local run folder keeps output easy to inspect during development, and MinIO preserves the same artifacts in a structured object-storage layout for repeatable runs.

- **MinIO** is part of the first working architecture. It stores JSON results and Markdown reports under `task_out/<run_id>/`, and it stores model artifacts under `model/trained_model/` when a model is trained or exported.
- **MLflow** remains an optional extension. It records run metadata such as the run ID, timestamp, model/provider name, model configuration, prompt version or hash, input summary, completion status, and validation results. It can link to or store the JSON files and report as artifacts.
- **MLflow with MinIO** can be configured to use object storage for MLflow artifacts, while MLflow tracks run metadata. The components have different responsibilities: MLflow indexes and describes runs; MinIO stores files.

MinIO is run from a Docker image, not as a manual local install. The project should use `docker-compose.yml` to start MinIO and the application together, with environment variables controlling the ports, bucket name, and credentials.

## 8. Suggested repository layout

**Reminder:** All services (including Jenkins!) are defined and started exclusively via `docker-compose.yml` as containers.


```text
crewai-business-plan-pipeline/
├── README.md
├── pyproject.toml                 # or requirements.txt, with pinned dependencies
├── .env.example                   # variable names only; no real secrets
├── .env                           # local only; never committed
├── .gitignore                     # .env, virtualenv, caches, generated runs
├── Dockerfile
├── docker-compose.yml             # app + MinIO + init service
├── Jenkinsfile                    # optional if using Jenkins instead of GitHub Actions
├── scripts/
│   ├── cleanup_docker.sh          # removes old containers/images for this project
│   └── init_minio.sh             # creates bucket and folders if needed
├── src/
│   └── business_plan/
│       ├── __init__.py
│       ├── main.py                # input and pipeline entry point
│       ├── crew.py                # single agent + three tasks + context ordering
│       ├── models.py              # Pydantic input and output models
│       ├── storage.py             # local outputs + MinIO upload logic
│       ├── config.py              # env-based settings
│       └── report.py              # deterministic Markdown report
├── tests/
│   ├── test_models.py
│   ├── test_context_flow.py
│   └── test_report.py
├── prompts/
│   └── example_business_idea.txt
├── runs/                          # generated locally; normally ignored by Git
└── .github/
    └── workflows/
        └── docker-compose-branch.yml  # optional branch-triggered automation
```

The sample input file is only a demonstration. The actual program should allow the user to supply a new prompt from the command line. A future FastAPI layer can provide an HTTP endpoint, but should reuse the same validated pipeline service rather than duplicate agent logic.

## 9. Secrets and responsible use

- Store the model API key in a local `.env` file or Jenkins credential store; commit only `.env.example`.
- Add `.env`, private outputs, caches, and generated run folders to `.gitignore` unless the user intentionally selects specific sanitized artifacts for version control.
- Avoid putting real customer data or confidential business information in prompts unless the model provider and data-handling choices are appropriate.
- Label estimates and market statements as assumptions unless supported by cited research.
- Treat model-generated pricing, market size, competitor descriptions, and forecasts as hypotheses to verify.
- Apply output validation and report failures clearly rather than silently accepting malformed JSON.
- Do not expose Jenkins to the public internet without authentication and deliberate security configuration.

## 10. Milestones

### Milestone 1 — Define the structured workflow

Create the input model and three Pydantic output models. Agree on required fields, types, and validation rules. Confirm that each task has one clear purpose and a separate JSON output.

### Milestone 2 — Run the single-agent, three-task CrewAI pipeline locally

Accept a user-supplied idea. Reuse one agent across all three tasks, pass previous outputs as context, validate every response, save per-run JSON files, and render the final Markdown report. Upload the outputs to MinIO under `task_out/<run_id>/`.

### Milestone 3 — Add tests and Git

Test model validation, context hand-off, output file creation, MinIO upload logic, and report rendering without making paid model calls. Initialize the repository and push it to the user's personal GitHub account. Keep secrets and private generated outputs out of Git.

### Milestone 4 — Add Docker Compose and local MinIO runtime

Create a `docker-compose.yml` stack with the app and MinIO, using environment variables for ports, bucket names, credentials, and project naming. Add a cleanup script to remove old containers and images for the same project before a rebuild. Ensure the bucket and `task_out/` and `model/trained_model/` folders exist automatically.

### Milestone 5 — Configure branch-triggered rebuilds

Have GitHub Actions or Jenkins watch the selected branch, especially `docker_compose`, and rebuild the Docker Compose environment when code changes are detected. Verify that the rebuild starts cleanly, installs dependencies, and runs the automated checks.

### Milestone 6 — Learn webhook delivery (optional)

Configure a webhook relay/tunnel to forward GitHub's push notification to the local Jenkins webhook endpoint. Verify a test delivery and a resulting Jenkins build. Shut down or disable the relay when not in use.

### Milestone 7 — Add experiment tracking (optional)

Add one MLflow run per generated plan. Record safe metadata and validation results. Use MLflow to compare generated runs while MinIO continues to store the actual artifacts.

### Milestone 8 — Add FastAPI (optional)

Expose the existing pipeline through a small local API so a user can submit a new business idea without editing source code. Keep Jenkins or GitHub Actions focused on testing and delivery of code changes, not on restarting the API for every user prompt.

## 11. Definition of done

- No manual Jenkins or MinIO installation, configuration, or usage required—all setup, build, and pipeline functionality must work within containers managed by Docker Compose on Windows with Docker Desktop.


The core project is complete when:

- A user can submit a business idea without modifying Python source code.
- One CrewAI agent runs three sequential tasks and each receives the intended context.
- Each task produces a separate JSON file that validates against its Pydantic model.
- The three task outputs and final Markdown report are saved locally and uploaded to MinIO under `task_out/<run_id>/`.
- Model artifacts are stored under `model/trained_model/` when applicable.
- Tests can verify schemas, context flow, and MinIO upload logic without requiring a live model call.
- Docker Compose starts the local stack with env-based ports and credentials.
- A branch-triggered workflow such as `docker_compose` can clean old resources, rebuild the app, and run automated checks.
- API credentials are absent from the repository and build logs.
- The README explains that generated business recommendations need independent validation.

Webhook triggering, FastAPI, and MLflow remain optional extensions, while MinIO and Docker Compose are part of the first working architecture.

## 12. Recommended first implementation scope

For a manageable MLOps learning experience, build the first version with **one CrewAI agent + three sequential tasks + Pydantic + local JSON/report files + MinIO + Docker Compose + GitHub Free + branch-triggered rebuilds**. This teaches the core agent workflow, structured output, version control, object storage, and local automation without requiring a public network endpoint at the outset.

Then add features in this order:

1. Jenkins or GitHub Actions automation for the `docker_compose` branch, including cleanup and rebuild.
2. MLflow to compare and inspect generation runs.
3. A secure webhook relay to learn event-triggered Jenkins builds.
4. FastAPI if the user wants a reusable prompt-submission interface.

This ordering keeps the first result runnable while showing how each MLOps component adds a distinct capability.
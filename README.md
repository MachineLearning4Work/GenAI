# CrewAI Business Proposal API

A teaching-focused FastAPI service that accepts a business idea, runs three
dependent CrewAI tasks, validates every task result with Pydantic, and stores
the input, outputs, final proposal, and workflow metadata in MinIO. Jenkins
builds and validates the same application through an isolated Docker Compose
CI stack.

## Learning objectives

Students use this project to learn how to:

- define CrewAI agents and tasks in YAML;
- pass validated output from one task to the next;
- enforce structured LLM output with Pydantic;
- expose an asynchronous AI workflow through FastAPI;
- store reproducible workflow artifacts in MinIO;
- package and run services with Docker Compose; and
- build, test, smoke-test, and clean up an application from Jenkins.

## Verified project status

The project was reviewed and validated on **2026-11-01** with Docker Desktop and
Python 3.11:

| Check | Result |
| --- | --- |
| Local unit tests | **78 passed** |
| Docker unit tests | **78 passed** |
| CrewAI YAML configuration | Valid |
| Application image | Built successfully |
| Jenkins image and Docker/Compose tooling | Built and validated |
| Compose configuration | Valid |
| FastAPI health check | Passed; application reported healthy |
| MinIO AIStor license and startup | Validated |
| MinIO write/read/delete smoke test | Passed |
| Jenkins controller startup | Passed; login page available on port `8081` |
| Live OpenAI proposal generation | Not run during review to avoid API cost |

The application, MinIO, and Jenkins were all successfully started together.
A local Jenkins Pipeline job must still be created through the Jenkins UI for
each new Jenkins installation. Provider-backed proposal generation requires a
valid `OPENAI_API_KEY` and may incur API charges.

## Quick start

### 1. Verify prerequisites

Install or provide:

- Python 3.11, 3.12, or 3.13;

- Docker Desktop with Docker Compose;

- a valid `minio.license` file in the repository root;

- an OpenAI API key for live proposal generation; and

- Git when Jenkins will check out this repository.

Confirm Docker is ready:

```powershell
docker info
docker compose version
```

### 2. Configure the environment

On a fresh clone, create the local environment file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set these required values:

```dotenv

MINIO_ROOT_USER=choose-a-unique-user

MINIO_ROOT_PASSWORD=choose-a-long-random-password

API_ACCESS_TOKEN=choose-a-long-random-token

OPENAI_API_KEY=your-provider-key
```

Do not commit `.env` or `minio.license`. Existing prepared environments should
keep their current `.env` file instead of overwriting it.

### 3. Start the application and MinIO
 Please check docker-compose.yml

```powershell
cd C:\......\mlops_project03_jenkins_modified_27Oct2026
```
Then, 

```powershell
docker compose up --build -d app minio
docker compose ps
docker compose exec -T app python scripts/smoke_test.py
```

NOTE: One important distinction:

- docker compose exec:
     runs a command inside an existing, running container.

- docker compose run :
       creates a new, one-off container to execute a command.


```powershell
docker compose run --rm app python --version
[+] run 1/1
 ✔ Container crewai-minio-1 Running                                                                                 0.0s
Container crewai-app-run-f0bd356278a0 Creating
Container crewai-app-run-f0bd356278a0 Created
Python 3.11.18

```
Create a new temporary container using the configuration of the app service, execute python --version inside it, and remove the container when finished (Above Script)


#### 3.1 Compare all three commands :

Command,	What does it do?,	Creates a new container?

docker compose up,	Starts services,	If needed

docker compose run,	Runs a one-off command,	Yes

docker compose exec,	Executes a command in an existing running container,	No


NOTE: 

docker compose exec : 

Executes a command inside an existing running service container.

You do not need to rebuild your images or restart your containers to run this smoke test.


```powershell
Smoke test passed: API health, authentication, and MinIO write/read/delete
```

Another example: Open a terminal inside the container:

```powershell
docker compose exec app bash
root@d708ba44ffa5:/app# python --version
Python 3.11.18
```


These three commands are used to build, start, inspect, and test Docker containers for your application and MinIO service.

docker compose up --build -d app minio 

Docker Compose starts:
- app
- minio
- Any services that these two services depend on.


Therefore:

- app starts.

- minio starts because it is explicitly requested and is also a dependency of app.


- jenkins does NOT start.

Execute application-level connectivity and functionality tests.



NOTE:

```powershell
docker compose up --build -d
```

Docker Compose starts all services that are enabled by default, including their dependencies.

In your configuration:

Service,	Starts?,	Reason

app,	Yes,	Default service

minio,	Yes,	Default service

jenkins,	No,	Requires ci profile


Notice that Jenkins is excluded because you defined:

```powershell
jenkins:
  profiles: ["ci"]
```


#### 3.1 Docker Compose commands

docker compose ps,	List containers and their status.

docker compose logs -f app,	Follow application logs continuously.

docker compose logs -f minio,	Follow MinIO logs.

docker compose restart app,	Restart the application.

docker compose stop	Stop, services without removing containers.

docker compose down	Stop, and remove containers and networks.

docker compose down -v,	Also remove associated Compose-managed volumes (potentially deleting persistent data).

docker compose exec app bash : 
Open a Bash shell inside the application container, if Bash is installed.




Expected smoke-test result:

```text
Smoke test passed: API health, authentication, and MinIO write/read/delete
```

Open:

- FastAPI health: <http://localhost:8000/health>
- MinIO Console: <http://localhost:9001>

### 4. Start Jenkins

```powershell

docker compose --profile ci up --build -d jenkins

docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

NOTE: 

These two commands are used to start Jenkins using Docker Compose and retrieve its initial administrator password so you can complete the Jenkins installation and configuration through your browser.


#### 4.1 Jenkins Profile 

```powershell
docker compose --profile ci up --build -d jenkins
```

This command starts the Jenkins service defined in your docker-compose.yml file.
Component	Explanation : 

docker compose	: Uses Docker Compose to manage multiple containers and services.

--profile ci	: Enables the ci profile, allowing services assigned to that profile to be started.
up	Creates and starts the requested services.

--build	Builds or rebuilds the Docker image if necessary before starting.

-d	Detached mode: runs containers in the background.


jenkins	Specifies the Jenkins service to start.


#### 4.2 Jenkins administrator password

```powershell
docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

The initial administrator password is generated during the first Jenkins initialization. Because /var/jenkins_home is persisted in a Docker volume, restarting the container normally does not generate a new initial password.

Copy the displayed value into Administrator password, then select Continue. The password persists in the jenkins_home Docker volume.


#### 4.3  Jenkins Setup 

Open <http://localhost:8081>, complete the Jenkins setup wizard, and create a
**Pipeline** job using **Pipeline script from SCM**. Select this Git repository
and set **Script Path** to `Jenkinsfile`.


#### 4.4 Jenkins Pipeline Configuration

Create a Jenkins **Pipeline** job and select **Pipeline script from SCM**.

Use the following configuration:

- **SCM:** Git
- **Repository URL:**

  ```text
  https://github.com/MachineLearning4Work/GenAI.git
  ```


Credentials: - none -


Branch Specifier:

```text
*/feature/mlops_project03_jenkins_v3
```

Repository browser: (Auto)

Script Path:

```text
Jenkinsfile
```

Keep Lightweight checkout enabled, then click Save and Build Now.



#### 4.5  Reset Jenkins and Retrieve the Initial Administrator Password

If Jenkins is already running and you have forgotten the administrator password, you can reset Jenkins to its initial state by stopping the container, removing it, deleting its persistent volume, and rebuilding it.

**Important:** Deleting the Jenkins volume removes all Jenkins data, including users, jobs, plugins, credentials, and configurations. It does not remove MinIO data if you delete only the Jenkins volume.

##### 1. Check the Running Containers

From the project directory, run:

```powershell
docker compose ps
```

Identify the Jenkins container and confirm that it is running.

##### 2. Identify the Jenkins Volume

Inspect the Jenkins container's volume mapping:

```powershell
docker inspect crewai-jenkins-1 --format "{{json .Mounts}}"
```

Alternatively, list all Docker volumes:

```powershell
docker volume ls
```

For this project, the Jenkins volume is:

```text
crewai_jenkins_home
```

The MinIO volume is separate:

```text
crewai_minio_data
```

**Do not delete the MinIO volume.**

##### 3. Stop the Jenkins Container

Stop only the Jenkins service:

```powershell
docker compose stop jenkins
```

This stops Jenkins without stopping the other services.

##### 4. Remove the Jenkins Container

Remove the stopped Jenkins container:

```powershell
docker compose rm -f jenkins
```

This removes the container but does not automatically delete its persistent volume.

##### 5. Delete the Jenkins Persistent Volume

Remove the Jenkins volume to start with a clean installation:

```powershell
docker volume rm crewai_jenkins_home
```

Verify that it has been removed:

```powershell
docker volume ls
```

The `crewai_jenkins_home` volume should no longer appear.

**Note:** This is the critical step that resets Jenkins. Simply stopping, starting, or rebuilding the container does not reset the persistent Jenkins configuration.

##### 6. Rebuild and Start Jenkins

Rebuild the Jenkins image and start the service using the CI profile:

```powershell
docker compose --profile ci up --build -d jenkins
```

This command:
- Builds the Jenkins image if necessary.
- Creates a new Jenkins container.
- Creates a new Jenkins home volume if it does not already exist.
- Starts Jenkins in detached mode.

##### 7. Check Jenkins Initialization

Check the Jenkins container status:

```powershell
docker compose ps
```

Review the initialization logs:

```powershell
docker compose logs -f jenkins
```

Wait until Jenkins has completed its startup process. Press `Ctrl+C` to exit the log display without stopping Jenkins.

##### 8. Retrieve the Initial Administrator Password

Execute the following command:

```powershell
docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Jenkins generates an initial administrator password during its first initialization.

Copy the displayed password.

##### 9. Unlock Jenkins and Complete the Setup

Open Jenkins in your browser:

```text
http://localhost:8081
```

Follow these steps:

1. Paste the initial administrator password into the **Unlock Jenkins** page.
2. Click **Continue**.
3. Select **Install suggested plugins**.
4. Create a new administrator account with your preferred username and password.
5. Complete the Jenkins configuration.

**Important:** Keep your new administrator credentials in a secure location.

## 10. Important Docker Commands: Summary

| Command | Purpose |
|---|---|
| `docker compose stop jenkins` | Stop Jenkins |
| `docker compose start jenkins` | Start an existing stopped Jenkins container |
| `docker compose rm -f jenkins` | Remove the stopped Jenkins container |
| `docker volume ls` | List Docker volumes |
| `docker volume rm crewai_jenkins_home` | Delete Jenkins persistent data |
| `docker compose --profile ci up --build -d jenkins` | Rebuild and start Jenkins |
| `docker compose logs -f jenkins` | Monitor Jenkins logs |
| `docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword` | Retrieve the initial administrator password |

**Key takeaway:** Docker containers and Docker volumes have different lifecycles. Removing and recreating a Jenkins container does not reset Jenkins if its persistent volume is retained. To perform a completely fresh Jenkins installation, the Jenkins container and its associated persistent volume must both be removed.






### 5. Stop the services

```powershell
docker compose --profile ci down
```

Add `--volumes` only when the Jenkins configuration and MinIO data should also be deleted:

```powershell
docker compose --profile ci down --volumes
```

This command stops and removes the containers, networks, and volumes associated with your Docker Compose project, including the persistent Jenkins data.





#### 5.1 Component Explanation 

docker compose : 	Manages your Docker Compose application.

--profile ci : 	Activates the ci profile and includes services assigned to it.

down :	Stops and removes the containers and networks created by Compose.

--volumes : 	Also removes the named volumes and anonymous volumes 
associated with the Compose project.



#### 5.2 down vs. down --volumes

Command,	Containers,	Networks,	Persistent volumes

docker compose down,	Removed,	Removed,	Preserved


docker compose down --volumes,	Removed,	Removed,	Removed

### 6. Architecture

```text
Authenticated POST /business-proposals
  → validate and persist input
  → pending → running
  → MarketResearch (structured Pydantic output)
  → BusinessStrategy (receives validated market research)
  → BusinessPlanReview (receives both validated outputs)
  → validate and persist final proposal
  → completed

Authenticated GET /business-proposals/{proposal_id}
  → return workflow state or retrieve the completed proposal from MinIO
```

One `BusinessPlanner` agent performs all three sequential tasks. The agent and
task descriptions are in `src/business_plan/config/agents.yaml` and
`src/business_plan/config/tasks.yaml`; the Python CrewAI integration assigns the version-supported `Task.output_pydantic` model to each task. Outputs are validated again before they are passed to the next task. Invalid results or provider failures stop the workflow and produce a safe failed status.



The repository has no database, durable queue, or worker. To preserve its existing architecture, the API uses FastAPI `BackgroundTasks` and writes local status/artifact copies under `RUNS_DIR`, while the proposal endpoints require successful MinIO writes. A process restart can interrupt an active job; multiple API replicas do not share a locking or idempotency store. Use a durable queue and transactional status store before deploying this prototype at scale.

#### 6.1 Repository map

```text
.
├── Jenkinsfile                         # Declarative CI pipeline
├── Dockerfile                          # FastAPI/CrewAI application image
├── docker-compose.yml                  # Local app, AIStor, and Jenkins services
├── docker-compose.ci.yml               # Isolated Jenkins test-stack overrides
├── jenkins/Dockerfile                  # Jenkins with Docker and required plugins
├── scripts/smoke_test.py               # Real API/authentication/MinIO smoke test
├── src/business_plan/
│   ├── api.py                          # FastAPI endpoints and authentication
│   ├── workflow.py                     # Three-step proposal orchestration
│   ├── crew.py                         # CrewAI agent/task construction
│   ├── models.py                       # Pydantic request/output contracts
│   ├── storage.py                      # Local artifact persistence
│   ├── object_store.py                 # Strict and best-effort MinIO operations
│   └── config/
│       ├── agents.yaml                 # BusinessPlanner role, goal, and backstory
│       └── tasks.yaml                  # Task prompts and expected outputs
└── tests/                              # Unit and API tests with external calls mocked
```

#### 6.2 CrewAI configuration explained

The workflow uses one focused `BusinessPlanner` agent rather than one agent per step. This keeps the example economical while showing how multiple CrewAI tasks can share one agent and pass validated context forward.

##### Agent settings

`src/business_plan/config/agents.yaml` defines:

- `role`: the agent's business-planning specialty;
- `goal`: the outcome and quality standards;
- `backstory`: expertise and evidence-aware working style;
- `allow_delegation: false`: prevents unnecessary agent-to-agent delegation; and
- `verbose: false`: keeps API and Jenkins logs readable.

`src/business_plan/crew.py` adds runtime safety limits:

- `max_iter=10` limits reasoning loops;
- `max_execution_time=300` caps a task at five minutes; and
- `max_retry_limit=1` limits provider-level retries.

The model is selected with `CREWAI_LLM`, using
`openai/gpt-4o-mini` by default. `OPENAI_BASE_URL` can point to an
OpenAI-compatible endpoint. The current integration intentionally accepts only model identifiers beginning with `openai/`.

##### Task sequence

| Order | Task | Input dependency | Structured output |
| --- | --- | --- | --- |
| 1 | `MarketResearch` | Submitted business idea | Customers, assumptions, trends, competitors, opportunities, risks, and sources |
| 2 | `BusinessStrategy` | Business idea and validated market research | Positioning, pricing, go-to-market, operations, KPIs, and mitigations |
| 3 | `BusinessPlanReview` | Business idea plus both validated prior outputs | Feasibility review, gaps, risks, readiness score, recommendation, and next steps |

Each task is created with `Task.output_pydantic`. The workflow validates the result again before storing it or passing it to the next task. A malformed task result stops the workflow and records a safe failure status instead of passing untrusted output downstream.

The research agent has no live web-search tool. We should treat generated market claims as hypotheses and can extend the lesson by adding a search tool, source-validation task, and appropriate API credentials.



##### Jenkins pipeline explained

The declarative `Jenkinsfile` performs these stages:

1. **Checkout** — checks out the selected branch and creates a build-specific Compose project name.

2. **Validate prerequisites** — checks Docker, Compose, the AIStor license, and the merged Compose configuration.

3. **Build image** — builds the application image from the reviewed source.

4. **Validate CrewAI configuration** — loads and validates the agent/task YAML.

5. **Unit tests** — runs the complete pytest suite and publishes JUnit results.

6. **Start API and MinIO** — creates an isolated, port-free CI stack and copies the license into its named volume.

7. **Smoke test** — verifies API health, bearer authentication, bucket creation, and MinIO object write/read/delete.

8. **Post-build cleanup** — captures failure logs and removes only that build's containers, volumes, and application image.

The Jenkins build does **not** call OpenAI. This keeps CI deterministic and prevents model charges on every source change. Live generation is tested manually through the authenticated API when desired.






##### Requirements and setup

- Python 3.11, 3.12, or 3.13 (CrewAI 1.15.28 does not support Python 3.14)
- Docker Desktop for the Compose setup
- An OpenAI API key (optionally for an OpenAI-compatible endpoint)
- MinIO running and reachable
- A long random API bearer token

If `.env` already exists, keep it: the prepared local environment has generated MinIO credentials and an API token, and only `OPENAI_API_KEY` needs your value. The default OpenAI endpoint/model and local service settings are already set. Never overwrite that file with the blank template.

On a fresh clone, copy the sample environment file and set secrets in `.env`:

```powershell
Copy-Item .env.example .env
```

##### Bearer Token setup (IMPORTANT)

 

Set `OPENAI_API_KEY` and replace `API_ACCESS_TOKEN` with a securely generated value. Set unique `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` values as well. Generate the API token with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

A Bearer Token is a secret authentication value (similar to a password) that a client must provide when accessing a protected API. In your MLOps project, API_ACCESS_TOKEN is used to protect your FastAPI application from unauthorized access.

Let's understand it step by step.

A **Bearer Token** is a secret credential (similar to a password) used to authenticate requests to your FastAPI application.

When a client sends an HTTP request, it must include the token in the `Authorization` header:

```http

POST /predict HTTP/1.1
Host: localhost:8000
Authorization: Bearer your_secret_token
Content-Type: application/json

```


Add the generated value to your `.env` file:

```env
API_ACCESS_TOKEN=YOUR_GENERATED_TOKEN
```

**How it works:**

- The client includes the Bearer Token when calling the API.

- FastAPI validates the token against `API_ACCESS_TOKEN`.

- Valid token: Access is granted.

- Invalid or missing token: Access is denied (`401 Unauthorized`).

**Security:** Keep this token secret. Never commit your `.env` file or expose your token in Git repositories.

Sample code 

```python 
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import secrets

app = FastAPI()

security = HTTPBearer()

API_ACCESS_TOKEN = os.getenv("API_ACCESS_TOKEN")

def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    if not API_ACCESS_TOKEN or not secrets.compare_digest(
        credentials.credentials,
        API_ACCESS_TOKEN
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )

    return credentials.credentials


@app.get("/protected")
def protected_endpoint(token: str = Depends(verify_token)):
    return {"message": "Access granted"}

```


##### .env file  (IMPORTANT)


`.env` is ignored by Git. Never commit provider credentials, MinIO passwords, API access tokens, or Jenkins credentials.

| Variable | Default | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | empty | Provider credential; required to create a proposal |
| `OPENAI_MODEL` | `gpt-4o-mini` | Legacy model label shown by `/health` |
| `CREWAI_LLM` | `openai/gpt-4o-mini` | CrewAI OpenAI-provider model identifier |
| `OPENAI_BASE_URL` | empty | Optional OpenAI-compatible API base URL |
| `API_ACCESS_TOKEN` | empty | Required bearer token for all data endpoints |
| `MINIO_ENDPOINT` | `minio:9000` | MinIO host and port; use `localhost:9000` outside Compose |
| `MINIO_ROOT_USER` | not set | MinIO access key; required for Compose and proposal storage |
| `MINIO_ROOT_PASSWORD` | not set | MinIO secret; required for Compose and proposal storage |
| `MINIO_BUCKET_NAME` | `business-plan-bucket` | Bucket created on first use |
| `MINIO_ENABLED` | `true` | Proposal API refuses work when storage is disabled |
| `MINIO_SECURE` | `false` | Use HTTPS for MinIO when enabled |
| `MINIO_CONNECT_TIMEOUT` | `3` | Bounded connection timeout in seconds |
| `MINIO_READ_TIMEOUT` | `10` | Bounded read timeout in seconds |
| `RUNS_DIR` | `<repo>/runs` | Local status and artifact mirror |
| `APP_PORT` | `8000` | API host port in Compose |
| `MINIO_PORT` | `9000` | MinIO S3 host port |
| `MINIO_CONSOLE_PORT` | `9001` | MinIO console host port |

The `.env.example` leaves credentials blank so the application fails closed
until values are configured. Use strong unique values in shared environments.
The `/health` endpoint is public and masks the provider key; all proposal and
legacy run-data endpoints require `Authorization: Bearer <API_ACCESS_TOKEN>`.`.

## 7. Run locally

Install the project and test dependencies:

```powershell
python -m pip install -e . "pytest>=8.2,<9" "httpx>=0.28.1,<0.29"
```

### 7.1 Test setup 

"pytest>=8.2,<9"	Installs pytest version 8.2 or higher, but lower than 9.
"httpx>=0.28.1,<0.29"	Installs HTTPX version 0.28.1 or higher, but lower than 0.29.

"pytest" is a Python testing framework.

It allows you to write and execute automated tests.

Example:

```python
def add(a, b):
    return a + b


def test_add():
    assert add(2, 3) == 5

```


For a host-run API, set `MINIO_ENDPOINT=localhost:9000` and start MinIO
separately. Then:

```powershell
$env:PYTHONPATH = 'src'
uvicorn business_plan.api:app --host 127.0.0.1 --port 8000
```

## 8. Run with Docker Compose

Start the API and MinIO (Jenkins is opt-in):

```powershell
docker compose up --build -d app minio
docker compose logs -f app minio
```

Stop the local services:

```powershell
docker compose down
```

This repository pins the tested MinIO AIStor RELEASE.2026-09-19T17-05-25Z
image by digest and mounts the existing `minio.license` read-only, explicitly
passing it to the server. 


Keep this private file in the repository root on your machine; it is excluded from Git and Docker build contexts. A missing, expired, or invalid license prevents a successful storage
smoke test. 

See [MinIO AIStor on Windows with Docker Desktop](guide\MinIO_AIStor_on_Windows_with_Docker_Desktop.md)
for license setup.

Check the real API and storage (no OpenAI calls):

```powershell
docker compose exec -T app python scripts/smoke_test.py
```

The check verifies API health, bearer authentication, and MinIO bucket creation
and object write/read/delete, rather than treating API liveness as proof that
storage works.

### 8.1  API Health Check - 

The health endpoint is public:

```powershell
curl.exe http://localhost:8000/health
```
response : 

```powershell
{"status":"ok","runs_dir":"/app/runs","openai":{"configured":true,"key":"sk-...4nEA","model":"gpt-4o-mini"},"object_store":{"enabled":true,"reachable":true,"bucket":"business-plan-bucket","detail":null}}
```


Why is it public?

It does not require a Bearer Token. This allows monitoring tools, Docker health checks, or administrators to check whether the API is available without authentication.

## 9. Submit a Business Proposal

This section explains how to submit a business proposal through the API endpoint:

`POST http://localhost:8000/business-proposals`

There are two ways to configure the Bearer token before submitting a proposal:

1. **Option 1:** Use the existing API access token configured in the `.env` file.
2. **Option 2:** Generate a new secure token, update the `.env` file, and recreate the Docker container so that the application uses the new token.

### 9.1 Option 1 – Use the Existing API Access Token

First, open the project's `.env` file and locate the existing API access token.

For example:

```env
API_ACCESS_TOKEN=abc123
```

**Step 1. Configure the token in Anaconda Prompt**

Open Anaconda Prompt in your project directory (or the terminal where you will execute the API requests).

Set the environment variable to the same value configured in `.env`:

```cmd
set API_ACCESS_TOKEN=abc123
```

Verify that the environment variable has been set:

```cmd
echo %API_ACCESS_TOKEN%
```

Expected output:

```text
abc123
```

**Step 2. Submit a business proposal**

Make sure that `payload.json` exists in your current working directory.

Execute the following command in Anaconda Prompt:

```cmd
curl.exe -X POST http://localhost:8000/business-proposals ^
  -H "Authorization: Bearer %API_ACCESS_TOKEN%" ^
  -H "Content-Type: application/json" ^
  -H "Idempotency-Key: example-business-montreal-003" ^
  --data-binary "@payload.json"
```

**Note:** The caret character (`^`) is the Windows CMD line-continuation character. It allows you to split a long command across multiple lines. Do not add spaces after the caret.

**Step 3. Check the API response**

If the request is accepted, the API returns HTTP `202 Accepted` with a proposal ID.

Example response (illustrative):

```json
{
  "proposal_id": "b3a95f878fc6489c88b2b7e8b5824e76",
  "status": "pending",
  "task": null,
  "error": null
}
```

Copy the returned `proposal_id` and store it in an environment variable:

```cmd
set PROPOSAL_ID=b3a95f878fc6489c88b2b7e8b5824e76
```

Verify the variable:

```cmd
echo %PROPOSAL_ID%
```

**Step 4. Check the proposal status**

Use the following GET request to check the progress of the submitted proposal:

```cmd
curl.exe http://localhost:8000/business-proposals/%PROPOSAL_ID% ^
  -H "Authorization: Bearer %API_ACCESS_TOKEN%"
```

Possible response (illustrative):

```json
{
  "proposal_id": "b3a95f878fc6489c88b2b7e8b5824e76",
  "status": "failed",
  "error": {
    "code": "TASK_FAILED",
    "task": "MarketResearch",
    "message": "The proposal workflow could not complete this task."
  }
}
```

The proposal may initially have a `pending` status. You can repeat the GET request to monitor its progress until it reaches a final status (`completed` or `failed`).

---

### 9.2 Option 2 – Generate a New API Access Token and Recreate the Docker Container

Use this option when you want to replace the existing API access token with a newly generated secure token.

**Step 1. Generate a secure Bearer token**

Execute the following command in Anaconda Prompt:

```cmd
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Example output (illustrative):

```text
YOUR_GENERATED_TOKEN_HERE
```

Copy the generated token.

**Step 2. Update the project's `.env` file**

Open the `.env` file in your project directory and replace the existing token:

```env
API_ACCESS_TOKEN=PASTE_YOUR_GENERATED_TOKEN_HERE
```

**Important:**
- Do not include quotation marks around the token.
- Do not add spaces before or after the `=` sign.
- Keep the token secret. Do not commit your `.env` file or expose the token in GitHub.

**Step 3. Recreate the Docker container**

The application must receive the updated environment variable.

If the token is passed to the application through Docker Compose, changing `.env` alone does not update an already-running container. You must recreate the application container.

From the directory containing `docker-compose.yml` or `compose.yml`, execute:

```cmd
docker compose up -d --build --force-recreate app
```

Alternatively, you can recreate all services:

```cmd
docker compose down
docker compose up -d --build
```

**Note:** The first command recreates only the `app` service (and starts its required dependencies if they are not already running). The second command stops the Compose application and starts all services defined in the Compose configuration.

To identify the available service names, execute:

```cmd
docker compose config --services
```

Example output:

```text
minio
app
```

**Step 4. Verify that the new token is available inside the application container**

You can check whether the environment variable exists inside the running container without displaying the actual secret:

```cmd
docker compose exec app sh -c "if [ -n \"$API_ACCESS_TOKEN\" ]; then echo API_ACCESS_TOKEN is set; else echo API_ACCESS_TOKEN is missing; fi"
```

Expected output:

```text
API_ACCESS_TOKEN is set
```

This confirms that the environment variable is available inside the application container. It does not display or verify the token's actual value.

**Step 5. Configure the new token in Anaconda Prompt**

The token configured in the Windows environment must match the token configured in `.env`.

Execute:

```cmd
set API_ACCESS_TOKEN=PASTE_YOUR_GENERATED_TOKEN_HERE
```

Verify that it has been configured:

```cmd
echo %API_ACCESS_TOKEN%
```

You are now ready to submit a business proposal using the new token.

**Step 6. Submit a business proposal**

Execute the following command:

```cmd
curl.exe -X POST http://localhost:8000/business-proposals ^
  -H "Authorization: Bearer %API_ACCESS_TOKEN%" ^
  -H "Content-Type: application/json" ^
  -H "Idempotency-Key: example-business-montreal-003" ^
  --data-binary "@payload.json"
```

The API should return HTTP `202 Accepted` with a proposal ID and a `pending` status.

Example response (illustrative):

```json
{
  "proposal_id": "unique-id",
  "status": "pending"
}
```

**Step 7. Monitor the proposal**

Copy the returned proposal ID:

```cmd
set PROPOSAL_ID=PASTE_RETURNED_PROPOSAL_ID_HERE
```

Check the proposal status:

```cmd
curl.exe http://localhost:8000/business-proposals/%PROPOSAL_ID% ^
  -H "Authorization: Bearer %API_ACCESS_TOKEN%"
```

Repeat the GET request as needed to monitor the workflow.

---

### 9.3 Understanding the API Responses and Workflow

The business proposal endpoint executes an asynchronous, LLM-backed workflow using CrewAI.

The API initially accepts the request and returns a proposal ID. The actual workflow continues in the background.

The status endpoint can return the following states:

| Status | Description |
|---|---|
| `pending` | The proposal has been accepted and is waiting for processing. |
| `running` | The workflow is executing. The response may include the current task. |
| `completed` | The workflow has successfully completed and generated the final proposal. |
| `failed` | The workflow encountered an error. The response includes a safe error category and the failed task. |

### 9.4 HTTP Status Codes

The API uses the following HTTP status codes:

| HTTP Status | Description |
|---|---|
| `202 Accepted` | The proposal has been accepted for asynchronous processing. |
| `401 Unauthorized` | The Bearer token is missing or invalid. |
| `404 Not Found` | The requested proposal ID does not exist. |
| `409 Conflict` | An existing idempotency key was reused with a different request body. |
| `422 Unprocessable Entity` | The submitted input does not satisfy the validation requirements. |
| `503 Service Unavailable` | Required LLM or MinIO configuration is unavailable. |

### 9.5 Idempotency-Key

Clients can optionally include an `Idempotency-Key` HTTP header when submitting a business proposal.

For example:

```cmd
-H "Idempotency-Key: example-business-montreal-003"
```

The purpose of this key is to prevent duplicate proposal submissions when a client retries the same request.

The behavior is as follows:

- **Same key + same request body:** The API returns the existing proposal instead of scheduling duplicate work.
- **Same key + different request body:** The API returns `409 Conflict`.
- **Different key:** The API treats the request as a new proposal.

The key can contain up to 200 non-whitespace characters.

**Important:** The idempotency mapping is stored locally and protected only within a single API process. It does not provide a distributed idempotency guarantee across multiple API instances.

### 9.6 Business Proposal Input and Generated Output

The incoming business idea must contain the following fields:

**Required fields:**

- `name`: Name of the business idea.
- `description`: Description of the proposed business.
- `target_market`: Intended target market.

**Optional fields:**

- `location`: Proposed business location.
- `budget`: Estimated budget.
- `additional_context`: Any additional information relevant to the proposal.

Input fields and string lengths are validated using Pydantic.

The generated final JSON contains:

- `proposal_id`
- The original business idea.
- Three validated workflow outputs.
- An executive summary.
- A final recommendation.
- An ISO-8601 creation timestamp.
- The completed workflow status.

### 9.7 Legacy API Endpoints

The following endpoints remain available for compatibility with the original deterministic teaching demonstration:

- `/submit`
- `/status/{run_id}`
- `/runs/{run_id}/artifacts`

These endpoints are authenticated but do not execute the CrewAI workflow.

**Important:** For the actual LLM-backed business proposal workflow, use:

`POST /business-proposals`

and retrieve its status using:

`GET /business-proposals/{proposal_id}`



## MinIO artifact layout

The configured bucket stores:

```text
business-proposals/{proposal_id}/input.json
business-proposals/{proposal_id}/market-research.json
business-proposals/{proposal_id}/business-strategy.json
business-proposals/{proposal_id}/business-plan-review.json
business-proposals/{proposal_id}/final-proposal.json
business-proposals/{proposal_id}/metadata.json
```

JSON objects use `application/json`. A local mirror is also written under
`RUNS_DIR/{proposal_id}/`. The new proposal workflow fails visibly when an
artifact cannot be uploaded or retrieved; the legacy `/submit` pipeline keeps
its existing best-effort MinIO mirroring behavior.

## Tests and CI

Run the unit suite without external API keys or MinIO:

```powershell
python -m pytest
```

Tests mock CrewAI task execution and MinIO. Jenkins builds the image, validates
CrewAI YAML, runs the unit suite with JUnit results, then checks the real API and
AIStor storage. OpenAI calls are disabled in CI, so no provider key is required.
This is validation, not a deployment or a build for each business idea.

### Bundled local Jenkins

```powershell
docker compose --profile ci up --build -d jenkins
docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Open <http://localhost:8081>, unlock Jenkins with the displayed initial password,
and create your administrator account. The custom image includes Docker CLI,
Buildx, Compose, Git/Pipeline, credentials, timestamps, and JUnit plugins. The setup
wizard remains enabled; Jenkins is bound only to the local loopback interface.
The `DOCKER_GID=0` setting works with Docker Desktop; Linux hosts must use the
numeric group owning `/var/run/docker.sock`.

Create a **Pipeline** job, select **Pipeline script from SCM**, choose Git,
configure this repository and branch (plus Git credentials if private), and set
**Script Path** to `Jenkinsfile`. Commit/push the reviewed source changes first
so Jenkins checks out the same version. Do not commit `.env` or the license.

The bundled Jenkins mounts your license at `/run/secrets/minio.license`.
No Jenkins MinIO/OpenAI credentials need to be entered for normal CI: its
throwaway stack uses CI-only credentials and publishes **no host ports**.
`docker-compose.ci.yml` requires Compose 2.24.4 or newer and uses named volumes,
so it also works when Jenkins talks to the host Docker daemon through the
socket. The license is streamed into the CI container with `docker compose cp`;
a Jenkins-workspace bind mount would incorrectly resolve on the Docker host.

Each job/build gets a separate Compose project. Cleanup removes only that
build's containers and volumes, never the local application, MinIO data, or
Jenkins home. The CI API is intentionally not left running after a build.
An external Linux Jenkins agent must supply Docker/Compose and a readable valid
license at `MINIO_LICENSE_FILE` (or adapt the pipeline to a Jenkins Secret file).

**Local-development trust boundary:** Docker socket access gives Jenkins jobs
control of the Docker host. Run only trusted jobs; do not expose this controller
or run untrusted pull-request code with these privileges.

There are no application webhook endpoints. Configure source-control webhooks
at the Git hosting provider to trigger Jenkins, and use the authenticated
FastAPI endpoint for business ideas. Do not connect business-idea submissions
to image builds or deployments.

## Known limitations

- In-process background work is not durable and is not safe for horizontal
  scaling; a restart may lose an active job.
- Status files and local files do not provide database transactions, distributed
  locking, or cross-replica idempotency.
- The research task has no search tools configured, so it must state evidence
  limitations and must not claim to have verified live market facts.
- MinIO AIStor requires a valid local license; licenses and previously tracked
  secrets must also be removed from repository history before public sharing.
- Production deployments should configure authentication, strong credentials,
  TLS, a durable worker/status store, request rate limits, and monitoring.

## Jenkins setup notes

### Unlock the Jenkins administrator account

Jenkins stores its one-time initial administrator password inside the Jenkins
container at `/var/jenkins_home/secrets/initialAdminPassword`. From a PowerShell
terminal opened in the repository root, run:

```powershell
docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Copy the displayed value into the **Administrator password** field at
<http://localhost:8081>, select **Continue**, install the suggested plugins, and
create the first administrator account. Treat the initial password as a secret;
do not add it to `.env`, source control, screenshots, or course materials.

The Jenkins configuration persists in the `jenkins_home` Docker volume. Normal
container restarts therefore do not require the initial unlock process again.
Removing the volume with `docker compose --profile ci down --volumes` deletes
the configured Jenkins instance and requires setup again on the next start.

### Create the project Pipeline job

Starting the Jenkins container does not automatically create a job. On the
**Start a job** page:

1. Select **Create a job**.
2. Enter `crewai-mlops-pipeline` as the job name.
3. Select **Pipeline**, then select **OK**.
4. In the **Pipeline** section, choose **Pipeline script from SCM**.
5. Set **SCM** to **Git**.
6. Set **Repository URL** to
   `https://github.com/MachineLearning4Work/GenAI.git`.
7. Add Jenkins Git credentials if the repository is private.
8. Set **Branch Specifier** to the branch that contains this project. For the
   reviewed branch, use `*/feature/mlops_project03_jenkins_v3`.
9. Set **Script Path** to `Jenkinsfile`.
10. Select **Save**, then select **Build Now**.

The job reads `Jenkinsfile` from the selected remote branch. Local uncommitted
changes are not available to Jenkins, so commit and push the intended README,
source, test, Compose, and pipeline changes before building.

### Pipeline from SCM
Pipeline script from SCM is a Jenkins Pipeline configuration option that tells Jenkins to retrieve the pipeline definition (usually a Jenkinsfile) directly from a source code management (SCM) repository, such as GitHub, GitLab, or Azure DevOps.

In simple terms:

Instead of writing your Jenkins pipeline directly inside the Jenkins web interface, you store the pipeline code in your Git repository. Jenkins retrieves and executes it automatically.

#### Sample Project
Imagine your MLOps project has this structure:

mlops_project03_jenkins/
│
├── Jenkinsfile
├── requirements.txt
├── Dockerfile
├── src/
│   └── train.py
├── tests/
│   └── test_model.py
└── README.md

The Jenkinsfile contains your CI/CD pipeline instructions.

For example:

pipeline {
    agent any

    stages {

        stage('Checkout') {
            steps {
                echo 'Checking out source code'
            }
        }

        stage('Install Dependencies') {
            steps {
                bat 'pip install -r requirements.txt'
            }
        }

        stage('Run Tests') {
            steps {
                bat 'pytest tests/'
            }
        }

        stage('Build') {
            steps {
                echo 'Building MLOps project'
            }
        }
    }
}

### Why Jenkins is this recommended 


For your MLOps teaching project, I recommend Pipeline script from SCM because:
- Your Jenkinsfile is version-controlled alongside your Python code.
- Students can review pipeline changes through Git commits.
- You can maintain different pipeline versions using Git branches.
- You can collaborate with other developers.
- You can reproduce and maintain CI/CD workflows.
One important concept: Your Python source code and Jenkinsfile are both stored in Git, but they serve different purposes:
- train.py: Implements machine learning logic.
- Jenkinsfile: Defines how Jenkins builds, tests, and deploys your ML application.
You can think of the Jenkinsfile as the automation blueprint for your MLOps project.

### Understand the build result

Open **Build History**, select the build number, and inspect **Console Output**.
A successful run performs checkout, prerequisite validation, application-image
build, CrewAI configuration validation, 78 unit tests, API/MinIO startup, the
storage smoke test, JUnit publication, and isolated cleanup.

Useful local Jenkins commands:

```powershell
# Show service status
docker compose --profile ci ps

# Follow Jenkins logs
docker compose --profile ci logs -f jenkins

# Restart Jenkins without deleting its configuration
docker compose --profile ci restart jenkins

# Stop the stack while preserving data
docker compose --profile ci down
```

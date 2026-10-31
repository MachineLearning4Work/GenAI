# CrewAI Business Proposal API

A FastAPI service that accepts a business idea, runs three dependent CrewAI
tasks, validates every task result with Pydantic, and stores the input, outputs,
final proposal, and workflow metadata in MinIO.

## Architecture

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
`src/business_plan/config/tasks.yaml`; the Python CrewAI integration assigns
the version-supported `Task.output_pydantic` model to each task. Outputs are
validated again before they are passed to the next task. Invalid results or
provider failures stop the workflow and produce a safe failed status.

The repository has no database, durable queue, or worker. To preserve its
existing architecture, the API uses FastAPI `BackgroundTasks` and writes local
status/artifact copies under `RUNS_DIR`, while the proposal endpoints require
successful MinIO writes. A process restart can interrupt an active job; multiple
API replicas do not share a locking or idempotency store. Use a durable queue
and transactional status store before deploying this prototype at scale.

## Requirements and setup

- Python 3.11, 3.12, or 3.13 (CrewAI 1.15.28 does not support Python 3.14)
- Docker Desktop for the Compose setup
- An OpenAI API key (optionally for an OpenAI-compatible endpoint)
- MinIO running and reachable
- A long random API bearer token

If `.env` already exists, keep it: the prepared local environment has generated
MinIO credentials and an API token, and only `OPENAI_API_KEY` needs your value.
The default OpenAI endpoint/model and local service settings are already set.
Never overwrite that file with the blank template.

On a fresh clone, copy the sample environment file and set secrets in `.env`:

```powershell
Copy-Item .env.example .env
```

Set `OPENAI_API_KEY` and replace `API_ACCESS_TOKEN` with a securely generated
value. Set unique `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` values as well.
Generate the API token with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

`.env` is ignored by Git. Never commit provider credentials, MinIO passwords,
API access tokens, or Jenkins credentials.

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
legacy run-data endpoints require `Authorization: Bearer <API_ACCESS_TOKEN>`.

## Run locally

Install the project and test dependencies:

```powershell
python -m pip install -e . "pytest>=8.2,<9" "httpx>=0.28.1,<0.29"
```

For a host-run API, set `MINIO_ENDPOINT=localhost:9000` and start MinIO
separately. Then:

```powershell
$env:PYTHONPATH = 'src'
uvicorn business_plan.api:app --host 127.0.0.1 --port 8000
```

## Run with Docker Compose

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
passing it to the server. Keep this private file in the
repository root on your machine; it is excluded from Git and Docker build
contexts. A missing, expired, or invalid license prevents a successful storage
smoke test. See
[MinIO AIStor on Windows with Docker Desktop](guide/MinIO%20AIStor%20on%20Windows%20with%20Docker%20Desktop.md)
for license setup.

Check the real API and storage (no OpenAI calls):

```powershell
docker compose exec -T app python scripts/smoke_test.py
```

The check verifies API health, bearer authentication, and MinIO bucket creation
and object write/read/delete, rather than treating API liveness as proof that
storage works.

## API

The health endpoint is public:

```powershell
curl.exe http://localhost:8000/health
```

Submit a proposal:

```powershell
curl.exe -X POST http://localhost:8000/business-proposals `
  -H "Authorization: Bearer $env:API_ACCESS_TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"business_idea":{"name":"Example Business","description":"A short business idea","target_market":"Local small businesses","location":"Montreal","budget":"$25,000","additional_context":"Start with a small pilot"}}'
```

The API returns HTTP `202 Accepted` with a pending proposal ID:

```json
{
  "proposal_id": "unique-id",
  "status": "pending"
}
```

Poll the proposal:

```powershell
curl.exe http://localhost:8000/business-proposals/<proposal_id> `
  -H "Authorization: Bearer $env:API_ACCESS_TOKEN"
```

The response contains `pending`, `running` (including the current task),
`completed` (including the proposal), or `failed` (including a safe error
category and task). Input errors return `422`; missing proposals return `404`;
missing LLM or MinIO configuration returns `503`; invalid bearer tokens return
`401`.

Clients may include an `Idempotency-Key` header (up to 200 non-whitespace
characters). Repeating the same key and request body returns the existing
proposal instead of scheduling duplicate work; reusing the key with different
input returns `409 Conflict`. The mapping is stored locally and guarded only
within one API process, so it is not a distributed idempotency guarantee.

The incoming idea fields are `name`, `description`, and `target_market`
(required), plus optional `location`, `budget`, and `additional_context`.
String lengths are validated with Pydantic. The generated final JSON contains
`proposal_id`, the original idea, all three validated outputs, an executive
summary, a final recommendation, an ISO-8601 creation timestamp, and the
completed status.

`/submit`, `/status/{run_id}`, and `/runs/{run_id}/artifacts` remain for
compatibility with the original deterministic teaching demo. They are
authenticated but do not call CrewAI; use `/business-proposals` for the real
LLM-backed workflow.

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

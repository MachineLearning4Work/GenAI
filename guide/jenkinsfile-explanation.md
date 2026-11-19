# Jenkinsfile Detailed Explanation

This is a **Jenkins Declarative Pipeline** written using **Groovy syntax**. Its purpose is to:

1. Check out the application source code.
2. Validate Docker and configuration prerequisites.
3. Build the application Docker image.
4. Validate the CrewAI configuration.
5. Run unit tests.
6. Start the API and MinIO services.
7. Run a smoke test.
8. Publish test reports and clean up temporary Docker resources.

The pipeline uses Docker Compose to run the application and supporting services.

---

## 1. Main pipeline structure

```groovy
pipeline {
    agent any
    options { ... }
    environment { ... }
    stages { ... }
    post { ... }
}
```

| Section | Purpose |
|---|---|
| `agent` | Selects the Jenkins machine that runs the pipeline |
| `options` | Configures pipeline behavior |
| `environment` | Defines environment variables |
| `stages` | Defines the work Jenkins must perform |
| `post` | Defines actions after the pipeline finishes |

---

## 2. Agent selection

```groovy
agent any
```

This tells Jenkins to run the pipeline on any available Jenkins agent.

The selected agent must have the necessary tools installed, including:

- Docker
- Docker Compose
- Permission to run Docker commands
- Access to the MinIO license file

A more specific configuration could be:

```groovy
agent {
    label 'docker-agent'
}
```

That would restrict the pipeline to an agent labeled `docker-agent`.

---

## 3. Pipeline options

```groovy
options {
    timestamps()
    disableConcurrentBuilds()
    skipDefaultCheckout(true)
    timeout(time: 45, unit: 'MINUTES')
}
```

### `timestamps()`

Adds timestamps to Jenkins console output. This helps identify slow operations and understand when commands ran.

### `disableConcurrentBuilds()`

Prevents two builds of this Jenkins job from running at the same time. This helps avoid conflicts involving Docker containers, networks, volumes, and shared files.

### `skipDefaultCheckout(true)`

Stops Jenkins from automatically checking out the code. The pipeline performs checkout explicitly in its `Checkout` stage:

```groovy
checkout scm
```

### `timeout(time: 45, unit: 'MINUTES')`

The entire pipeline may run for no longer than 45 minutes. If it exceeds that time, Jenkins stops it.

---

## 4. Environment variables

```groovy
environment {
    COMPOSE_FILE = 'docker-compose.yml:docker-compose.ci.yml'
    MINIO_ROOT_USER = 'ci-minio'
    MINIO_ROOT_PASSWORD = 'ci-only-disposable-password'
    API_ACCESS_TOKEN = 'ci-only-disposable-api-token'
    OPENAI_API_KEY = ''
    MINIO_LICENSE_FILE = '/run/secrets/minio.license'
}
```

Variables defined in the `environment` block are available to Jenkins shell commands and Docker Compose.

### `COMPOSE_FILE`

```groovy
COMPOSE_FILE = 'docker-compose.yml:docker-compose.ci.yml'
```

This tells Docker Compose to combine two files:

1. `docker-compose.yml`
2. `docker-compose.ci.yml`

The CI file commonly overrides or extends the base Compose configuration for testing.

The equivalent command-line form is:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.ci.yml \
  config
```

### MinIO credentials

```groovy
MINIO_ROOT_USER = 'ci-minio'
MINIO_ROOT_PASSWORD = 'ci-only-disposable-password'
```

These variables provide credentials for the MinIO service. They are intended for disposable CI use, not production.

Even disposable credentials should ideally be stored in Jenkins Credentials instead of being committed to source control.

### API token

```groovy
API_ACCESS_TOKEN = 'ci-only-disposable-api-token'
```

This token is probably used by the application to authenticate API requests during CI.

### Empty OpenAI key

```groovy
OPENAI_API_KEY = ''
```

This disables or prevents OpenAI API access during the CI run. The application may use a mock or local mode instead.

### MinIO license path

```groovy
MINIO_LICENSE_FILE = '/run/secrets/minio.license'
```

This is the path where Jenkins expects to find the MinIO license file. The pipeline checks the file and later copies it into the MinIO container.

---

## 5. Stages

The stages execute in this order:

1. Checkout
2. Validate prerequisites
3. Build image
4. Validate CrewAI configuration
5. Unit tests
6. Start API and MinIO
7. Smoke test

---

## 6. Checkout stage

```groovy
stage('Checkout') {
    steps {
        checkout scm
        script {
            env.COMPOSE_PROJECT_NAME = "ci-${env.BUILD_TAG}".toLowerCase().replaceAll('[^a-z0-9_-]', '-')
        }
    }
}
```

### `checkout scm`

```groovy
checkout scm
```

Checks out the source code from the SCM configured for the Jenkins job. For a Git job, this includes the repository, branch, commit, and credentials configured in Jenkins.

Here, `scm` is a Jenkins-provided object representing the job's source-control configuration.

### The `script` block

```groovy
script {
    ...
}
```

Declarative Pipeline syntax has some restrictions. The `script` block allows more general Groovy code, such as calculations and conditional logic.

### Creating a unique Compose project name

```groovy
env.COMPOSE_PROJECT_NAME = "ci-${env.BUILD_TAG}"
    .toLowerCase()
    .replaceAll('[^a-z0-9_-]', '-')
```

`env.BUILD_TAG` is a Jenkins variable that identifies the build. For example, it might contain a value similar to:

```text
jenkins-my-job-42
```

The final project name might be:

```text
ci-jenkins-my-job-42
```

`.toLowerCase()` converts the value to lowercase.

`.replaceAll('[^a-z0-9_-]', '-')` replaces characters that are not lowercase letters, numbers, underscores, or hyphens with a hyphen.

The result is stored in `env`, so later shell commands can use:

```bash
echo "$COMPOSE_PROJECT_NAME"
```

---

## 7. Validate prerequisites stage

```groovy
stage('Validate prerequisites') {
    steps {
        sh '''
          set -eu
          docker info >/dev/null
          docker compose version
          test -s "$MINIO_LICENSE_FILE"
          docker compose config -q
        '''
    }
}
```

The `sh` step runs shell commands on the Jenkins agent. Triple single quotes allow a multiline shell script.

### `set -eu`

- `-e`: Stop immediately if a command fails.
- `-u`: Treat an unset variable as an error.

Together, these options make the script fail early instead of continuing after an error.

### Check Docker

```bash
docker info >/dev/null
```

Confirms that the Docker daemon is available. Output is hidden by redirecting it to `/dev/null`.

### Check Docker Compose

```bash
docker compose version
```

Confirms that Docker Compose is installed and prints its version.

### Check the license file

```bash
test -s "$MINIO_LICENSE_FILE"
```

Confirms that the license file exists and is not empty. The `-s` test means the file must have a size greater than zero.

### Validate Compose configuration

```bash
docker compose config -q
```

Validates the merged Docker Compose configuration without starting containers. It can detect invalid YAML, bad service definitions, and configuration errors.

---

## 8. Build image stage

```groovy
stage('Build image') {
    steps {
        sh 'docker compose build app'
    }
}
```

This builds the Docker image for the `app` service using the Compose files.

A typical service definition might contain:

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
```

If the Dockerfile or dependency installation fails, this stage fails and later stages normally do not run.

---

## 9. Validate CrewAI configuration stage

```groovy
stage('Validate CrewAI configuration') {
    steps {
        sh 'docker compose run --rm --no-deps app python -c "from business_plan.crew import validate_crew_configuration; validate_crew_configuration()"'
    }
}
```

This runs a temporary container using the `app` service and executes Python code inside it:

```python
from business_plan.crew import validate_crew_configuration
validate_crew_configuration()
```

### `docker compose run`

Creates a one-time container for a command such as a test, migration, or validation task.

### `--rm`

Removes the temporary container after the command finishes.

### `--no-deps`

Does not start dependent services such as MinIO or a database. This validation only needs the application image and Python modules.

If the function raises an exception or the command exits with a nonzero status, Jenkins marks the stage as failed.

---

## 10. Unit tests stage

```groovy
stage('Unit tests') {
    steps {
        sh '''
          set -eu
          mkdir -p reports
          rm -f reports/junit.xml
          docker compose run --name "$COMPOSE_PROJECT_NAME-tests" --no-deps -e MINIO_ENABLED=false app python -m pytest --junitxml=/tmp/junit.xml
        '''
    }
    post {
        always {
          sh 'docker cp "$COMPOSE_PROJECT_NAME-tests:/tmp/junit.xml" reports/junit.xml || true'
          junit testResults: 'reports/junit.xml', allowEmptyResults: true
        }
    }
}
```

### Prepare the report directory

```bash
mkdir -p reports
```

Creates the `reports` directory if it does not already exist.

### Remove an old report

```bash
rm -f reports/junit.xml
```

Removes a previous report so Jenkins does not accidentally publish stale test results.

### Run pytest

```bash
docker compose run \
    --name "$COMPOSE_PROJECT_NAME-tests" \
    --no-deps \
    -e MINIO_ENABLED=false \
    app \
    python -m pytest \
    --junitxml=/tmp/junit.xml
```

This runs the tests in a temporary `app` container.

`--name` gives the container a predictable name, which is needed later when copying the report.

`--no-deps` prevents dependent services from starting.

`-e MINIO_ENABLED=false` sets an environment variable inside the test container, so unit tests do not need MinIO.

`python -m pytest` runs pytest using the container's Python environment.

`--junitxml=/tmp/junit.xml` writes the test results in Jenkins-compatible JUnit XML format.

---

## 11. Publishing unit-test results

```groovy
post {
    always {
        sh 'docker cp "$COMPOSE_PROJECT_NAME-tests:/tmp/junit.xml" reports/junit.xml || true'
        junit testResults: 'reports/junit.xml', allowEmptyResults: true
    }
}
```

The `always` block runs whether tests pass or fail. This allows Jenkins to collect test results even when some tests fail.

### Copy the report from the container

```bash
docker cp "$COMPOSE_PROJECT_NAME-tests:/tmp/junit.xml" reports/junit.xml || true
```

Copies the report from inside the container to the Jenkins workspace.

`|| true` prevents this reporting step from causing another failure if the report or container does not exist.

### Publish the report

```groovy
junit testResults: 'reports/junit.xml', allowEmptyResults: true
```

The Jenkins JUnit plugin reads the report and displays passed, failed, skipped, and timed-out tests.

`allowEmptyResults: true` prevents report publishing from failing the build when no report was generated. If you want missing reports to be treated as errors, use `false` instead.

---

## 12. Start API and MinIO stage

```groovy
stage('Start API and MinIO') {
    steps {
        sh '''
          set -eu
          docker compose create minio
          docker compose cp "$MINIO_LICENSE_FILE" minio:/licenses/minio.license
          docker compose up -d --wait --wait-timeout 120 app minio
        '''
    }
}
```

### Create the MinIO container

```bash
docker compose create minio
```

Creates the MinIO container without starting it. This gives the pipeline an opportunity to copy the license file before startup.

### Copy the license

```bash
docker compose cp "$MINIO_LICENSE_FILE" minio:/licenses/minio.license
```

Copies the license from the Jenkins agent into the MinIO container.

### Start the services

```bash
docker compose up -d --wait --wait-timeout 120 app minio
```

- `-d`: Run in detached mode.
- `--wait`: Wait for services to be running and healthy.
- `--wait-timeout 120`: Wait for up to 120 seconds.
- `app minio`: Start only these two services.

This gives the API and MinIO time to start before the smoke test executes.

---

## 13. Smoke test stage

```groovy
stage('Smoke test') {
    steps {
        sh 'docker compose exec -T app python scripts/smoke_test.py'
    }
}
```

This runs a basic health check inside the already-running `app` container.

A smoke test may verify that:

- The API responds.
- The application can connect to MinIO.
- Authentication works.
- A basic business operation completes.

### `docker compose exec`

Runs a command inside an existing running container. This differs from `docker compose run`, which creates a new temporary container.

### `-T`

Disables pseudo-terminal allocation. This is important in Jenkins because Jenkins is not an interactive terminal.

If the smoke test exits with a nonzero status, the stage and pipeline fail.

---

## 14. Pipeline failure logging

```groovy
post {
    failure {
        script {
            if (env.COMPOSE_PROJECT_NAME?.startsWith('ci-')) {
                sh 'docker compose logs --no-color --tail=100 app minio || true'
            }
        }
    }
```

This section runs only when the pipeline fails.

### Safe navigation operator

```groovy
env.COMPOSE_PROJECT_NAME?.startsWith('ci-')
```

The `?.` operator means that `startsWith()` is called only when `COMPOSE_PROJECT_NAME` is not null. This avoids a null-pointer error.

### Safety check

The name must begin with `ci-`. This helps ensure that diagnostic commands operate only on resources created by this CI pipeline.

### Print recent service logs

```bash
docker compose logs --no-color --tail=100 app minio || true
```

Prints the last 100 lines from the `app` and `minio` services. This helps diagnose startup and smoke-test failures.

- `--no-color`: Makes logs easier to read in Jenkins.
- `--tail=100`: Limits output to the last 100 lines.
- `|| true`: Prevents log collection from causing another failure.

---

## 15. Cleanup

```groovy
cleanup {
    script {
        if (env.COMPOSE_PROJECT_NAME?.startsWith('ci-')) {
            sh '''
              docker rm -f "$COMPOSE_PROJECT_NAME-tests" >/dev/null 2>&1 || true
              docker compose down --volumes --remove-orphans
              docker image rm "$COMPOSE_PROJECT_NAME-app" >/dev/null 2>&1 || true
            '''
        }
    }
}
```

The `cleanup` section runs after the pipeline finishes, whether it succeeds or fails.

### Remove the test container

```bash
docker rm -f "$COMPOSE_PROJECT_NAME-tests" >/dev/null 2>&1 || true
```

Stops and removes the named test container. Output and errors are hidden, and failure is ignored if the container was already removed.

### Stop services and remove volumes

```bash
docker compose down --volumes --remove-orphans
```

- Stops and removes Compose services.
- `--volumes` removes project volumes.
- `--remove-orphans` removes containers for services no longer defined in the current Compose files.

This is appropriate for disposable CI data but would be dangerous for production data.

### Remove the application image

```bash
docker image rm "$COMPOSE_PROJECT_NAME-app" >/dev/null 2>&1 || true
```

Attempts to remove the application image to save disk space on the Jenkins agent. The command ignores failure if the image is already gone or has a different name.

---

## 16. Complete execution flow

```text
Start Jenkins build
        |
        v
Select any available agent
        |
        v
Apply timeout and pipeline options
        |
        v
Checkout source code
        |
        v
Create unique Docker Compose project name
        |
        v
Check Docker, Compose, license, and YAML configuration
        |
        v
Build the app Docker image
        |
        v
Validate CrewAI configuration
        |
        v
Run unit tests
        |
        +--> Always copy and publish JUnit results
        |
        v
Create MinIO container
        |
        v
Copy MinIO license
        |
        v
Start app and MinIO
        |
        v
Run smoke test
        |
        v
If failure: show recent app and MinIO logs
        |
        v
Always clean containers, volumes, networks, and image
        |
        v
Finish Jenkins build
```

---

## 17. Important Jenkins concepts used

### Declarative Pipeline

The file starts with:

```groovy
pipeline {
```

Therefore, it uses Jenkins Declarative Pipeline syntax.

### Groovy syntax

Examples include:

```groovy
stage('Checkout')
```

```groovy
env.COMPOSE_PROJECT_NAME = ...
```

```groovy
if (...) {
    ...
}
```

```groovy
"${env.BUILD_TAG}"
```

### Jenkins environment variables

Common Jenkins variables include:

```groovy
env.BUILD_TAG
env.BUILD_NUMBER
env.BRANCH_NAME
env.JOB_NAME
env.WORKSPACE
env.BUILD_URL
```

Inside shell commands, they are accessed like this:

```bash
$BUILD_TAG
$WORKSPACE
```

### Jenkins Pipeline steps

Examples from this pipeline include:

```groovy
checkout scm
```

```groovy
sh 'command'
```

```groovy
junit testResults: 'reports/junit.xml'
```

These are Jenkins Pipeline steps, not ordinary operating-system commands.

---

## 18. Security recommendation

The following values are hardcoded in the Jenkinsfile:

```groovy
MINIO_ROOT_PASSWORD = 'ci-only-disposable-password'
API_ACCESS_TOKEN = 'ci-only-disposable-api-token'
```

Even disposable credentials can become visible in:

- Git history
- Jenkins source browsing
- Pull requests
- Build logs
- Backups

A safer approach is to store them in Jenkins Credentials:

```groovy
environment {
    COMPOSE_FILE = 'docker-compose.yml:docker-compose.ci.yml'
    MINIO_ROOT_USER = credentials('ci-minio-username')
    MINIO_ROOT_PASSWORD = credentials('ci-minio-password')
    API_ACCESS_TOKEN = credentials('ci-api-access-token')
    MINIO_LICENSE_FILE = '/run/secrets/minio.license'
}
```

The credential IDs must first be created in Jenkins under:

```text
Manage Jenkins -> Credentials
```

Avoid commands such as `env`, `printenv`, or `set` in build steps because they may print secrets into the Jenkins log.

---

## 19. Plain-English summary

This Jenkinsfile tells Jenkins:

> Take the latest application code, prepare an isolated Docker Compose environment, verify that Docker and the configuration are valid, build the application, validate the CrewAI setup, run unit tests, start the application and MinIO, run a smoke test, show useful logs if something fails, and remove all temporary CI resources afterward.

Overall, it is a well-structured CI pipeline because it includes:

- Explicit source checkout
- A global timeout
- Docker prerequisite checks
- Test report publishing
- Service health waiting
- Failure diagnostics
- Automatic cleanup
- Per-build Compose project isolation

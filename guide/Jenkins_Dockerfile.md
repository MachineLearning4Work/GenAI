# Jenkins CI Service

This setup runs Jenkins in Docker with the tools and permissions needed to build and manage Docker images and Docker Compose services from Jenkins pipelines.

## What this configuration provides

The Compose service creates a Jenkins container that:

- Uses a custom image built from `./jenkins/Dockerfile`.
- Starts only when the `ci` Compose profile is enabled.
- Persists Jenkins configuration, jobs, plugins, and credentials in the `jenkins_home` named volume.
- Uses the host Docker daemon through `/var/run/docker.sock`.
- Includes the Docker CLI, Docker Compose plugin, and Docker Buildx plugin.
- Installs a standard set of Jenkins Pipeline, Git, credentials, timestamp, and test-reporting plugins.
- Optionally mounts a MinIO license file into the container as a read-only secret.
- Binds Jenkins to localhost by default for safer local development.

## Project structure

```text
.
├── compose.yml                 # Docker Compose configuration
├── minio.license               # Optional MinIO license file
└── jenkins/
    └── Dockerfile              # Custom Jenkins image definition
```

The Compose file may also be named `docker-compose.yml`; use whichever filename exists in the project.

## Compose service explained

```yaml
jenkins:
  profiles: ["ci"]
```

The `ci` profile keeps Jenkins disabled unless it is explicitly requested. This is useful when the project has other services that do not always need a CI server.

```yaml
build:
  context: ./jenkins
```

Docker builds the Jenkins image using `jenkins/Dockerfile`. The build context is the `jenkins` directory.

```yaml
group_add:
  - "${DOCKER_GID:-0}"
```

The container is added to the group ID supplied by `DOCKER_GID`. This can allow the Jenkins process to access the Docker socket without running all Jenkins processes as root. If `DOCKER_GID` is not set, the fallback value is `0`.

> **Security note:** Access to `/var/run/docker.sock` is effectively root-level access to the host. Only use this configuration on a trusted machine and restrict access to Jenkins appropriately.

```yaml
ports:
  - "127.0.0.1:${JENKINS_PORT:-8081}:8080"
```

Jenkins listens on port `8080` inside the container. By default, it is available on the host at:

```text
http://localhost:8081
```

Set `JENKINS_PORT` to use a different host port:

```bash
JENKINS_PORT=9090 docker compose --profile ci up -d jenkins
```

The `127.0.0.1` binding means Jenkins is not exposed directly on the local network. If external access is required, place Jenkins behind a properly secured reverse proxy rather than exposing it casually.

### Volumes and mounts

```yaml
- jenkins_home:/var/jenkins_home
```

This named volume stores Jenkins data outside the container. Removing and recreating the container will not remove Jenkins jobs or configuration unless the volume is also deleted.

```yaml
- /var/run/docker.sock:/var/run/docker.sock
```

This gives Jenkins access to the host Docker daemon. Pipelines can therefore run commands such as `docker build`, `docker run`, and `docker compose`.

```yaml
- type: bind
  source: ./minio.license
  target: /run/secrets/minio.license
  read_only: true
  bind:
    create_host_path: false
```

The local `minio.license` file is mounted into the container at `/run/secrets/minio.license` as read-only. `create_host_path: false` prevents Docker Compose from silently creating an empty directory or file when the source is missing.

If the license is not needed by Jenkins, remove this mount. If it is needed, ensure the file exists before starting the service.

## Dockerfile explained

```dockerfile
FROM docker:29-cli AS docker_cli
```

This is a temporary build stage containing Docker CLI version 29 and its command-line plugins.

```dockerfile
FROM jenkins/jenkins:lts-jdk21
```

The final image is based on the official Jenkins LTS image running on Java 21.

```dockerfile
USER root
```

The Docker CLI binaries and plugins are copied into the Jenkins image as root because they need to be installed in system directories.

```dockerfile
COPY --from=docker_cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker_cli /usr/local/libexec/docker/cli-plugins/docker-compose /usr/local/libexec/docker/cli-plugins/docker-compose
COPY --from=docker_cli /usr/local/libexec/docker/cli-plugins/docker-buildx /usr/local/libexec/docker/cli-plugins/docker-buildx
```

These commands copy the following tools from the Docker CLI image into Jenkins:

- `docker`: the Docker command-line client.
- `docker compose`: the Docker Compose CLI plugin.
- `docker buildx`: the extended Docker build plugin.

The Docker daemon itself is not installed in the Jenkins image. Jenkins uses the host daemon through the mounted Docker socket.

```dockerfile
USER jenkins
```

After the tools are installed, the image switches back to the non-root `jenkins` user. This is the safer default for running Jenkins.

```dockerfile
RUN jenkins-plugin-cli --plugins workflow-aggregator pipeline-model-definition git credentials-binding timestamper junit
```

The image installs these Jenkins plugins at build time:

| Plugin | Purpose |
|---|---|
| `workflow-aggregator` | Provides the main Jenkins Pipeline feature set. |
| `pipeline-model-definition` | Supports declarative `Jenkinsfile` syntax. |
| `git` | Allows Jenkins to check out Git repositories. |
| `credentials-binding` | Makes stored credentials available to builds in a controlled way. |
| `timestamper` | Adds timestamps to build log output. |
| `junit` | Publishes JUnit-compatible test reports. |

## Prerequisites

Install the following on the host:

- Docker Engine or Docker Desktop with Compose v2 support.
- Permission to access the Docker daemon.
- A project directory containing the Compose file and `jenkins/Dockerfile`.
- `minio.license`, if the license mount is retained.

On Linux, determine the Docker group ID with:

```bash
getent group docker | cut -d: -f3
```

Start Jenkins with that value:

```bash
export DOCKER_GID="$(getent group docker | cut -d: -f3)"
docker compose --profile ci up -d --build jenkins
```

On Docker Desktop, the Docker socket and group behavior may differ. If Docker commands fail inside Jenkins, verify the Docker Desktop integration and the permissions available to the Jenkins container.

## Starting Jenkins

Build and start the service:

```bash
docker compose --profile ci up -d --build jenkins
```

View the container status:

```bash
docker compose --profile ci ps
```

Follow Jenkins logs:

```bash
docker compose --profile ci logs -f jenkins
```

Open Jenkins at [http://localhost:8081](http://localhost:8081), unless `JENKINS_PORT` was changed.

## Initial administrator password

For a fresh Jenkins volume, retrieve the initial administrator password with:

```bash
docker compose --profile ci exec jenkins \
  cat /var/jenkins_home/secrets/initialAdminPassword
```

Use that password on the first-run setup screen, then create the administrator account and complete the Jenkins setup wizard.

## Verifying Docker access

Check the Docker CLI inside the container:

```bash
docker compose --profile ci exec jenkins docker version
```

Check Docker Compose and Buildx:

```bash
docker compose --profile ci exec jenkins docker compose version
docker compose --profile ci exec jenkins docker buildx version
```

If these commands work but a pipeline cannot use Docker, check the pipeline's user permissions and the Docker socket group ID.

## Example Jenkinsfile

The following pipeline checks out a repository, builds an image, and runs a basic container command:

```groovy
pipeline {
    agent any

    environment {
        IMAGE_NAME = 'example-app'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build image') {
            steps {
                sh 'docker build -t "$IMAGE_NAME:$BUILD_NUMBER" .'
            }
        }

        stage('Docker check') {
            steps {
                sh 'docker run --rm "$IMAGE_NAME:$BUILD_NUMBER" --version || true'
            }
        }

        stage('Tests') {
            steps {
                sh 'mkdir -p test-results'
                // Replace this with the project's real test command.
                sh 'echo "<testsuite tests=\"0\"/>" > test-results/results.xml'
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results/*.xml'
                }
            }
        }
    }
}
```

For production pipelines, use Jenkins Credentials for registry passwords, SSH keys, tokens, and other secrets. Do not commit secrets to a repository or print them in build logs.

## Common operations

Stop Jenkins without deleting its data:

```bash
docker compose --profile ci stop jenkins
```

Restart Jenkins:

```bash
docker compose --profile ci restart jenkins
```

Rebuild after changing the Dockerfile or plugin list:

```bash
docker compose --profile ci up -d --build jenkins
```

Remove the container and network while preserving the named volume:

```bash
docker compose --profile ci down
```

Remove Jenkins and its persisted data as well:

```bash
docker compose --profile ci down -v
```

> **Warning:** `down -v` permanently deletes the `jenkins_home` volume, including jobs, credentials, plugins, and configuration. Back up Jenkins before using it.

## Troubleshooting

### Jenkins cannot connect to Docker

Confirm that the socket is mounted:

```bash
docker compose --profile ci exec jenkins ls -l /var/run/docker.sock
```

Confirm that the configured group ID matches the host Docker socket group:

```bash
stat -c '%g' /var/run/docker.sock
docker compose --profile ci exec jenkins id
```

Then rebuild or restart the service after changing `DOCKER_GID`.

### The MinIO license mount fails

Confirm that the source file exists and is a regular file:

```bash
test -f ./minio.license && echo 'MinIO license found'
```

Because `create_host_path` is disabled, Compose will fail rather than create a missing source path. This is intentional and helps catch configuration mistakes early.

### Jenkins starts but the browser cannot connect

Check the logs and port mapping:

```bash
docker compose --profile ci logs --tail=100 jenkins
docker compose --profile ci port jenkins 8080
```

If a different port is configured, use the value of `JENKINS_PORT`. Also verify that another process is not already using the selected host port.

### Plugin installation or image build fails

Rebuild with fresh output:

```bash
docker compose --profile ci build --no-cache jenkins
docker compose --profile ci up -d jenkins
```

The build requires internet access to download the base images and Jenkins plugins. Pinning plugin versions is recommended for repeatable production builds.

## Security considerations

This configuration is suitable for local development and trusted CI hosts, but it should be hardened before production use:

1. Treat Docker socket access as privileged host access.
2. Keep Jenkins bound to localhost or protect it with TLS, authentication, and a reverse proxy.
3. Back up the `jenkins_home` volume regularly.
4. Store secrets in Jenkins Credentials rather than source files or environment variables committed to Git.
5. Review and pin Jenkins plugin versions for reproducible builds.
6. Update the Jenkins base image and Docker CLI regularly.
7. Limit who can configure jobs and execute unrestricted pipeline scripts.
8. Consider a dedicated Docker builder or rootless build solution if direct host socket access is not acceptable.

## Summary

The Compose file runs a persistent Jenkins LTS controller with a Java 21 runtime. The custom image adds Docker CLI, Compose, and Buildx, while the mounted Docker socket lets Jenkins pipelines build and operate containers using the host Docker daemon. The `ci` profile keeps the service opt-in, and the `jenkins_home` volume preserves Jenkins state across container restarts and rebuilds.

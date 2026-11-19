# Understanding Docker Compose Build Output and Docker Layers

This section explains what happens when we run:

```powershell
docker compose up --build -d app minio
```

The command successfully builds the application image, downloads the MinIO image, creates the required Docker resources, and starts the application and MinIO containers.

---

## 1. Understanding the command

```powershell
docker compose up --build -d app minio
```

| Command part | Meaning |
|---|---|
| `docker` | Uses the Docker command-line interface. |
| `compose` | Uses Docker Compose to manage multiple related services. |
| `up` | Creates and starts the services. |
| `--build` | Builds the application image before starting the services. |
| `-d` | Runs the containers in detached mode, in the background. |
| `app minio` | Starts only the `app` and `minio` services. |

Docker Compose reads the service definitions from a file such as `docker-compose.yml` or `compose.yml`.

A simplified Compose file might look like this:

```yaml
services:
  app:
    build: .

  minio:
    image: quay.io/minio/aistor/minio:...
```

The `app` service is built locally from a `Dockerfile`. The `minio` service uses an image downloaded from a container registry.

---

## 2. What happened overall?

Docker performed the following process:

```text
Read the Compose file
        |
        +----------------------+
        |                      |
        v                      v
Build the app image      Pull the MinIO image
        |                      |
        +----------+-----------+
                   |
                   v
        Create network and volume
                   |
                   v
          Start two containers
```

In this example:

- The application image was built from the project source code.
- The MinIO image was pulled from the Quay container registry.
- A Docker network was created for communication between services.
- A Docker volume was created for persistent MinIO data.
- One container was started for the application and one for MinIO.

---

## 3. Reading the build output

### Loading the Dockerfile

```text
[internal] load build definition from Dockerfile
```

Docker reads the instructions in the project's `Dockerfile`. A Dockerfile is a recipe that describes how to build an image.

For example:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src/ /app/src/

RUN pip install --upgrade pip && pip install .

COPY tests/ /app/tests/
COPY scripts/ /app/scripts/

RUN mkdir -p /app/runs
```

Docker processes these instructions from top to bottom.

### Loading the base image

```text
load metadata for docker.io/library/python:3.11-slim
```

The application uses `python:3.11-slim` as its base image. This provides a small Linux environment with Python 3.11 already installed.

The base image is made of several downloadable pieces called **layers**.

### Loading `.dockerignore`

```text
[internal] load .dockerignore
```

The `.dockerignore` file identifies files that should not be sent to Docker during the build.

Typical entries include:

```text
.git
.venv
__pycache__
.pytest_cache
.env
```

This keeps the build context small, speeds up the build, and helps prevent secrets from being copied into the image.

### Loading the build context

```text
[internal] load build context
transferring context: 153.56kB
```

The **build context** is the project directory sent to Docker so that Docker can access files used by `COPY` instructions.

### Creating the working directory

```text
[stage-0 2/8] WORKDIR /app
```

This sets `/app` as the working directory inside the image. Later commands use this directory as their default location.

#### Docker Steps, Stages, and Layers

A **step** is one instruction or action in a Dockerfile, such as copying files, installing packages, or creating a directory.

A **stage** is one complete phase of the Docker image build. Each `FROM` instruction starts a new stage. This project has one stage because it has one `FROM` instruction.

A **layer** is a saved filesystem change created during the build. For example, copying source code or installing Python packages can create a layer. Docker combines the layers to create the final image.

In simple terms:

- **Steps** are the actions Docker performs.
- **Stages** are the sections in which those actions are performed.
- **Layers** are the saved results of those actions.

### Copying project files

```text
[stage-0 3/8] COPY pyproject.toml README.md /app/
[stage-0 4/8] COPY src/ /app/src/
```

These instructions copy files from the host project into the image:

```text
/app/
├── pyproject.toml
├── README.md
└── src/
```

### Installing Python packages

```text
[stage-0 5/8] RUN ... pip install ...
```

Docker executes the installation command inside the image. In this example, it upgrades `pip` and installs the Python project and its dependencies.

The following option creates a build cache for downloaded Python packages:

```text
--mount=type=cache,target=/root/.cache/pip
```

The cache helps future builds run faster. It is used during the build and should not be confused with the final image layers.

### Copying tests and scripts

```text
[stage-0 6/8] COPY tests/ /app/tests/
[stage-0 7/8] COPY scripts/ /app/scripts/
```

These instructions copy the project's tests and scripts into the image.

### Creating the runs directory

```text
[stage-0 8/8] RUN mkdir -p /app/runs
```

This creates `/app/runs` inside the image. The application can use this directory for run-related files.

---

## 4. What is a Docker layer?

A Docker image is not one large undivided file. It is built as a stack of read-only layers.

For example:

```text
+--------------------------------------+
| Layer: RUN mkdir -p /app/runs       |
+--------------------------------------+
| Layer: COPY scripts/ /app/scripts/  |
+--------------------------------------+
| Layer: COPY tests/ /app/tests/      |
+--------------------------------------+
| Layer: COPY src/ /app/src/          |
+--------------------------------------+
| Layer: RUN pip install .            |
+--------------------------------------+
| Layer: COPY project metadata        |
+--------------------------------------+
| Base Python and Linux layers        |
+--------------------------------------+
```

When a container runs, Docker combines these layers and presents them as one normal filesystem:

```text
/app/
├── pyproject.toml
├── README.md
├── src/
├── tests/
├── scripts/
└── runs/
```

Internally, however, this filesystem is assembled from multiple layers.

### Why Docker uses layers

Docker layers provide several benefits:

1. **Reuse**: Multiple images can share the same Python and Linux base layers.
2. **Caching**: Docker can reuse unchanged layers from previous builds.
3. **Efficient transfer**: Registries can transfer only layers that are missing.
4. **Faster builds**: Unchanged installation steps do not always need to run again.

For example, if only a source file changes, Docker may reuse the base image and the dependency-installation layer, rebuilding only the later layers.

---

## 5. Docker build cache and instruction order

Docker processes a Dockerfile from top to bottom. A change in an earlier instruction can invalidate the cache for later instructions.

This arrangement is often efficient:

```dockerfile
COPY pyproject.toml README.md /app/
RUN pip install .
COPY src/ /app/src/
```

If only a file under `src/` changes, Docker may reuse the dependency-installation layer.

However, if `pyproject.toml` changes, Docker may need to run `pip install .` again because the dependency definition may have changed.

This is why stable files are often copied before frequently changing source code.

---

## 6. Exporting the application image

After completing the Dockerfile instructions, Docker creates the final image:

```text
exporting to image
exporting layers
exporting manifest
exporting config
naming to docker.io/library/crewai-app:latest
```

The resulting image is named:

```text
crewai-app:latest
```

The name contains:

```text
crewai-app   # Image name
latest       # Image tag
```

The image is stored locally unless it is explicitly pushed to a registry.

### Manifest and configuration

An image contains more than filesystem layers:

```text
Image
├── Filesystem layers
├── Configuration
│   ├── Working directory
│   ├── Environment variables
│   ├── Entrypoint
│   └── Command
└── Manifest
    └── References the layers and configuration
```

The manifest acts like an index that describes the image. The `sha256` values are content-based identifiers used to identify and verify the exact image content.

---

## 7. What happened with MinIO?

Docker pulled the MinIO image from the Quay container registry:

```text
quay.io/minio/aistor/minio@sha256:107cf201...
```

An image can be referenced with a tag:

```yaml
image: minio/minio:latest
```

or with a digest:

```yaml
image: quay.io/minio/aistor/minio@sha256:107cf201...
```

A tag such as `latest` can point to different image versions over time. A digest identifies exact image content and therefore provides better reproducibility.

---

## 8. Image versus container

These terms are related but different.

### Image

An image is a packaged, reusable template containing the application, its dependencies, and the required filesystem.

Examples:

```text
python:3.11-slim
crewai-app:latest
quay.io/minio/aistor/minio:...
```

### Container

A container is a running instance created from an image.

In this example:

```text
Image                         Container
--------------------------    -----------------------
crewai-app:latest         ->  crewai-app-1
MinIO image               ->  crewai-minio-1
```

One image can be used to create multiple containers:

```text
crewai-app:latest
       |
       +--> crewai-app-1
       +--> crewai-app-2
       +--> crewai-app-3
```

---

## 9. The container writable layer

The layers in a Docker image are normally read-only. When Docker starts a container, it adds a small writable layer on top:

```text
+--------------------------------------+
| Container writable layer             |
| Temporary runtime changes            |
+--------------------------------------+
| Read-only application image layers  |
+--------------------------------------+
| Read-only Python/Linux base layers  |
+--------------------------------------+
```

If the application creates a file while running, that change is normally stored in the container's writable layer.

Because containers are designed to be replaceable, data stored only in this layer may disappear when the container is removed. Important data should be stored in a Docker volume or another persistent storage system.

---

## 10. What happened with the network?

Compose created this network:

```text
Network crewai_default Created
```

The network allows the services to communicate:

```text
crewai-app-1  <---->  crewai-minio-1
```

Within the Compose network, the application can normally reach MinIO using the service name, for example:

```text
http://minio:9000
```

Using the service name is better than using a container IP address because container IP addresses can change.

Docker Compose provides internal DNS so that service names can be resolved automatically.

---

## 11. What happened with the volume?

Compose created this volume:

```text
Volume crewai_minio_data Created
```

A Docker volume is persistent storage managed by Docker. It is commonly used for MinIO data.

```text
MinIO container
       |
       v
crewai_minio_data volume
       |
       v
Persistent object-storage data
```

If the MinIO container is removed and a new container is connected to the same volume, the stored data can remain available.

### Image layer versus volume

| Feature | Image layer | Docker volume |
|---|---|---|
| Purpose | Package application files | Store changing application data |
| Usually read-only? | Yes | No |
| Rebuilt with the image? | Often | No |
| Designed for persistence? | No | Yes |
| Example | Python and application code | MinIO objects |

Be careful with this command:

```powershell
docker compose down -v
```

The `-v` option removes the Compose volumes and can delete stored MinIO data.

---

## 12. Final result

The final output confirms that the deployment succeeded:

```text
✔ Image crewai-app Built
✔ Network crewai_default Created
✔ Volume crewai_minio_data Created
✔ Container crewai-minio-1 Started
✔ Container crewai-app-1 Started
```

The resulting Docker environment can be represented as:

```text
Docker Engine
│
├── Image: crewai-app:latest
│   └── Container: crewai-app-1
│
├── Image: MinIO image
│   └── Container: crewai-minio-1
│
├── Network: crewai_default
│   ├── crewai-app-1
│   └── crewai-minio-1
│
└── Volume: crewai_minio_data
    └── Persistent MinIO data
```

---

## 13. Useful commands for inspection

Show the Compose services and their status:

```powershell
docker compose ps
```

List local images:

```powershell
docker image ls
```

List running containers:

```powershell
docker ps
```

List all containers, including stopped containers:

```powershell
docker ps -a
```

List Docker volumes:

```powershell
docker volume ls
```

List Docker networks:

```powershell
docker network ls
```

View application logs:

```powershell
docker compose logs app
```

Follow application logs continuously:

```powershell
docker compose logs -f app
```

Open a shell inside the running application container:

```powershell
docker compose exec app sh
```

Stop the services while keeping volumes:

```powershell
docker compose down
```

Stop the services and remove their volumes:

```powershell
docker compose down -v
```

---

## 14. Short summary

Docker Compose reads the project configuration and identifies the required services. It builds the `app` image from the Dockerfile and downloads the MinIO image from a registry. The application image is composed of reusable, read-only layers. Docker then creates containers from the images, connects them through a private network, and uses a volume to preserve MinIO data.

The key concepts are:

> **An image is a packaged template. A container is a running instance of an image. Docker layers make images reusable and cacheable. A volume stores persistent data. A network allows services to communicate.**

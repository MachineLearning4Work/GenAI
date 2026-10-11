# CrewAI Business-Plan Pipeline (teaching-friendly)

Prerequisites:
- Windows with Docker Desktop installed and running


Quick start (tests and local run):

Run unit tests (requires Python installed):

```bash
# On Windows PowerShell (example using the workspace Python)
$env:PYTHONPATH='src'; C:/Python314/python.exe -m pytest -q
```

Run the minimal local pipeline (writes JSON outputs under `runs/`):

```bash
# Use the detected Python executable or your environment's python
C:/Python314/python.exe -c "import sys; sys.path.insert(0, 'src'); from business_plan.main import run; run('sample idea')"
```

Docker Compose (Jenkins + MinIO + app):

```bash
docker compose up --build -d
# to see logs: docker compose logs -f
API endpoints (async):
- Submit an idea (returns run_id immediately):

```bash
curl -X POST http://localhost:8000/submit -H "Content-Type: application/json" -d '{"idea":"My sample idea"}'
```

- Check run status:

```bash
curl http://localhost:8000/status/<run_id>
```
```

If Docker image pulls fail (rate limits or private registry), try logging into Docker Hub:

```bash
docker login
```

Jenkins first-time steps:

1. Visit http://localhost:8081
2. Retrieve the initial admin password from the `jenkins_home` volume (or from container logs):

```bash
docker compose logs jenkins
# look for the 'Please use the following password' message
```

3. Follow the setup wizard to install recommended plugins and create the pipeline job using the included `Jenkinsfile`.

This repository is intentionally minimal for teaching. See `project_brief_review/Project Proposal_ Local CrewAI Business-Plan Pipeline with Jenkins.md` for full design details.

MinIO notes, licensing, and Windows setup
---------------------------------------


Recommended MinIO image and license download for a single-node local (free) instance

- Preferred (community/standalone): `minio/minio:RELEASE` — this is the official MinIO server image. It is suitable for running a single-node local object store for development and teaching. If your environment blocks `docker pull` from Docker Hub, you may need to `docker login` or use an internal registry mirror.

- **To download the latest Aistor (MinIO Community Edition) Docker image with a free developer license, see:**
	- https://www.min.io/download/aistor-server
	- This page provides the latest image tag, instructions, and a link to obtain your free standalone license (required to run the container).
- Alternative vendor/editions (for example `quay.io/minio/aistor/minio:latest`) may require a license for certain features (as experienced in this project). If you run such an image it may deny bucket creation until a valid license is installed.

License guidance

- For a simple, local, single-node development instance prefer the official community image (no license needed for basic S3 operations). If you intentionally use a licensed/enterprise image, apply the license using the MinIO client (`mc`) or the MinIO Console as the vendor documents instruct.
- If you see the error: "Access denied. No license is installed. Please install a valid license using 'mc license update' to enable service." — that means the chosen image requires a license. Either switch to the official community image or install the vendor license.

Creating the bucket (two options)

1) MinIO Console (UI)

	 - Open: http://localhost:9001
	 - Login: `minioadmin` / `minioadmin` (defaults in `.env.example`) unless you changed them
	 - Buckets → Create bucket → name: `business-plan-bucket`

2) MinIO client (`mc`) — Windows PowerShell example

	 - Install `mc` on Windows: https://min.io/docs/minio/linux/reference/minio-mc.html
		 - Download the `mc` binary, place it on PATH, and verify with `mc --version`.

	 - Configure alias and create bucket:

```powershell
mc alias set myminio http://localhost:9000 minioadmin minioadmin
mc mb --ignore-existing myminio/business-plan-bucket
```

If you must install a vendor license using `mc` (for vendor images that require it):

```powershell
# apply license file to the running MinIO server
mc admin license update myminio C:\path\to\minio-license.json
```

Windows / Docker Desktop notes
-----------------------------

- Ensure Docker Desktop is running before using `docker compose`.
- If your environment uses a proxy or a registry mirror, Docker Desktop may be configured with HTTP/HTTPS proxy or "registry-mirrors". These settings can block direct pulls from Docker Hub for some images. To avoid pull failures:
	- Open Docker Desktop → Settings → Resources → Proxies and clear the proxy entries (or add exceptions for `registry-1.docker.io`, `index.docker.io`, and `min.io`).
	- Open Docker Desktop → Settings → Docker Engine and remove or update `registry-mirrors` if they do not mirror the images you need.
	- Restart Docker Desktop after changes.

- Authenticate to Docker Hub if you hit rate limits or pull access errors:

```powershell
docker login
```

Jenkins and Ports
-----------------

- Jenkins UI (this project): http://localhost:8081 (we mapped host 8081 → container 8080 to avoid common conflicts). If you expect 8080, check `docker compose ps`.

Debugging tips
--------------

- Check running containers and ports:

```powershell
docker compose ps
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
```

- View logs (example):

```powershell
docker compose logs web --tail=200
docker compose logs minio --tail=200
```


# MinIO AIStor on Windows with Docker Desktop

This guide shows how to run **MinIO AIStor** on Windows using the image:

```yaml
image: quay.io/minio/aistor/minio:latest
```

It covers the free, single-node license workflow, Docker Desktop with WSL 2, persistent storage, the AIStor Console, and common errors with solutions.

> **Scope:** The free tier license is intended for **one compute resource with one or more drives**. This guide is for local development, testing, and evaluation. It is not a distributed multi-node deployment guide. [1]

## 1. What you need

Install or prepare the following:

- Windows 11 Professional or a supported Windows Server version.
- Docker Desktop for Windows.
- Docker Desktop configured to use **Linux containers** and the **WSL 2 based engine**.
- A free AIStor license downloaded from the official MinIO page.
- At least 8 GB of RAM for evaluation. A virtualized or WSL-based environment benefits from 16–32 GB of RAM. [2]

Docker Desktop's WSL 2 backend provides the Linux kernel used by Linux containers. In Docker Desktop, open **Settings > General**, enable **Use the WSL 2 based engine**, and apply the change. If WSL integration is needed, enable it under **Settings > Resources > WSL Integration**. [3]

Check WSL from PowerShell:

```powershell
wsl.exe -l -v
```

The distribution used for development should show version `2`. If necessary:

```powershell
wsl.exe --set-default-version 2
```

> Do not install a second, independent Docker Engine inside WSL while Docker Desktop is running. Two Docker installations can conflict. [3]

## 2. Get the free AIStor license

1. Open the official page: <https://www.min.io/download/aistor-server>
2. Select **Windows** if you are reviewing the Windows binary instructions, or select **Docker** if that option is shown for the container workflow.
3. Under **Free**, select the option to get started/request a license.
4. Complete the MinIO license request flow.
5. Download the license file named `minio.license`.

Create this Windows folder structure:

```text
C:\minio
C:\minio\data
C:\minio\minio.license
```

The final item must be a **file**, not a directory. If the browser downloaded `minio.license` to `Downloads`, move it into `C:\minio`:

```powershell
New-Item -ItemType Directory -Force C:\minio\data | Out-Null
Copy-Item "$HOME\Downloads\minio.license" C:\minio\minio.license -Force
```

Verify it:

```powershell
Get-Item C:\minio\minio.license
```

Do not paste the license token into a public issue, Git repository, Dockerfile, or screenshot. Treat it as a secret.

## 3. Pull the exact image requested

Open **PowerShell** and run:

```powershell
docker pull quay.io/minio/aistor/minio:latest
```

Confirm that the image is available:

```powershell
docker image inspect quay.io/minio/aistor/minio:latest
```

The `latest` tag is convenient for evaluation but can change over time. For repeatable deployments, record the version or digest that you tested and replace `latest` with that pinned reference later.

## 4. Start a single-node AIStor container

Set an administrator username and a strong password. The password below is only an example; replace it before starting the container.

```powershell
$AistorAdmin = "minioadmin"
$AistorPassword = "Change-this-to-a-long-random-password-123!"
```

Start AIStor:

```powershell
docker run -d `
  --name aistor `
  --restart unless-stopped `
  -p 9000:9000 `
  -p 9001:9001 `
  --env MINIO_ROOT_USER=$AistorAdmin `
  --env MINIO_ROOT_PASSWORD=$AistorPassword `
  --mount "type=bind,source=C:\minio\data,target=/mnt/data" `
  --mount "type=bind,source=C:\minio\minio.license,target=/minio.license,readonly" `
  quay.io/minio/aistor/minio:latest `
  server /mnt/data --license /minio.license --console-address ":9001"
```

The two ports are:

- **9000:** S3 API endpoint.
- **9001:** AIStor web Console.

Open the Console at <http://localhost:9001> and sign in with the values of `$AistorAdmin` and `$AistorPassword`.

Applications should use the S3 endpoint:

```text
http://localhost:9000
```

The `C:\minio\data` bind mount keeps objects on the Windows host when the container is removed and recreated. The license is mounted read-only at `/minio.license`, and the server is explicitly told to use that path.

## 5. Check that the container is healthy

Run these commands in PowerShell:

```powershell
docker ps

docker logs --tail 100 aistor

docker inspect aistor
```

A running container should show port mappings similar to:

```text
0.0.0.0:9000->9000/tcp
0.0.0.0:9001->9001/tcp
```

Test the endpoints:

```powershell
Invoke-WebRequest http://localhost:9000/minio/health/live
Invoke-WebRequest http://localhost:9000/minio/health/ready
```

If the container stops, inspect the exit status and logs:

```powershell
docker ps -a --filter name=aistor

docker inspect aistor --format '{{.State.ExitCode}}'
docker logs aistor
```

## 6. Stop, start, remove, and recreate

Stop and start the same container:

```powershell
docker stop aistor
docker start aistor
```

Follow the logs:

```powershell
docker logs -f aistor
```

If you change the `docker run` options, remove and recreate the container. Removing the container does **not** remove the data in `C:\minio\data`:

```powershell
docker stop aistor
docker rm aistor
```

Then run the start command again.

> Do not run `docker volume prune` or delete `C:\minio\data` unless you intentionally want to delete stored objects. Back up the data before destructive operations.

## 7. Optional: Docker Compose for Windows

Create `C:\minio\docker-compose.yml`:

```yaml
services:
  aistor:
    image: quay.io/minio/aistor/minio:latest
    container_name: aistor
    restart: unless-stopped
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: Change-this-to-a-long-random-password-123!
    volumes:
      - type: bind
        source: C:/minio/data
        target: /mnt/data
      - type: bind
        source: C:/minio/minio.license
        target: /minio.license
        read_only: true
    command: server /mnt/data --license /minio.license --console-address ":9001"
```

Use forward slashes in the Compose Windows paths. From `C:\minio`, run:

```powershell
Set-Location C:\minio
docker compose up -d
docker compose ps
docker compose logs -f aistor
```

For a real deployment, keep the password outside the Compose file by using an `.env` file or a secret-management system. Do not commit either the password or the license to source control.

## 8. Common errors and solutions

### Error: `docker is not recognized`

**Cause:** Docker Desktop is not installed, its CLI is not on `PATH`, or the terminal was opened before Docker Desktop was installed.

**Solution:**

1. Start Docker Desktop.
2. Close and reopen PowerShell.
3. Run:

```powershell
docker version
docker context ls
```

If `docker version` shows only a client and cannot contact the server, Docker Desktop or its Linux engine is not ready.

### Error: `Cannot connect to the Docker daemon`

**Cause:** Docker Desktop is stopped, still starting, or is using the wrong container mode.

**Solution:**

- Start Docker Desktop and wait until it reports that Docker is running.
- Switch to **Linux containers** from the Docker Desktop tray menu.
- Confirm **Use the WSL 2 based engine** is enabled.
- Retry:

```powershell
docker info
docker run --rm hello-world
```

### Error: `WSL integration ... failed` or `Unexpected WSL error`

**Cause:** WSL is outdated, the distribution is running as WSL 1, Docker Desktop integration is disabled, or a separate Docker Engine is conflicting with Docker Desktop.

**Solution:**

```powershell
wsl.exe --update
wsl.exe -l -v
```

Convert the relevant distribution to WSL 2 if needed:

```powershell
wsl.exe --set-version <DistributionName> 2
```

In Docker Desktop, check **Settings > Resources > WSL Integration**. Restart Docker Desktop after changing the setting. Remove or disable a separately installed Docker daemon inside WSL if Docker Desktop is the intended engine. [3]

### Error: `pull access denied`, `unauthorized`, or image not found

**Cause:** The registry name was mistyped, the network/proxy blocks Quay, or the image is not reachable from the current Docker engine.

**Solution:**

```powershell
docker logout quay.io
docker pull quay.io/minio/aistor/minio:latest
```

Check that the image name is exactly:

```text
quay.io/minio/aistor/minio:latest
```

If a corporate proxy, VPN, firewall, or TLS inspection device is present, configure its settings in Docker Desktop and confirm that `quay.io` is reachable. Do not replace the image with an unrelated `minio/minio` image when the goal is AIStor.

### Error: `invalid mount config`, `bind source path does not exist`, or `Mounts denied`

**Cause:** The host folder does not exist, the drive is not shared with Docker Desktop, or the path is malformed.

**Solution:**

```powershell
New-Item -ItemType Directory -Force C:\minio\data | Out-Null
Test-Path C:\minio\data
Test-Path C:\minio\minio.license
```

For Docker Desktop, allow the drive/folder under its file-sharing or resource settings if your version requests permission. Prefer a short path such as `C:\minio`. Docker's `--mount` syntax reports missing source paths instead of silently creating the wrong object. [4]

### Error: `not a directory`, `is a directory`, or the license cannot be opened

**Cause:** `C:\minio\minio.license` did not exist when a `-v` mount was created. Docker can create a missing `-v` source as a directory, so the container sees a directory at `/minio.license` instead of a file.

**Solution:**

```powershell
Get-Item C:\minio\minio.license
```

If it is a directory, remove only that empty mistaken directory and copy the real license file into its place:

```powershell
Remove-Item C:\minio\minio.license -Recurse
Copy-Item "$HOME\Downloads\minio.license" C:\minio\minio.license
```

Recreate the container using the `--mount` command in this guide. Confirm the mount:

```powershell
docker inspect aistor
```

The mount destination should be `/minio.license`, and the source should be the Windows license file.

### Error: `license required`, `license not found`, `invalid license`, or `license is expired`

**Cause:** The license was not mounted, the container command points to the wrong path, the file is corrupt or from another product/environment, or the license has expired.

**Solution:**

1. Confirm the Windows file exists:

```powershell
Test-Path C:\minio\minio.license
```

2. Confirm the container mount:

```powershell
docker inspect aistor
```

3. Confirm the server command contains both:

```text
--license /minio.license
```

4. Download a fresh license from the official MinIO flow if necessary.
5. Recreate the container after replacing the file.

AIStor license status can be checked with the AIStor Client command `mc license info`. An expired license can move through grace, read-only, and offline states. In read-only mode, writes fail with `403 AccessDenied`; after the offline threshold, S3 operations are blocked until a valid license is installed. [5]

### Error: `AccessDenied` after the server starts

**Cause:** This can mean invalid credentials, an expired license in read-only/offline mode, or an S3 policy issue.

**Solution:**

- Check that the Console credentials match `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` used when the container was created.
- Check the server logs:

```powershell
docker logs aistor
```

- If the error says that writes are not allowed because of the license, renew or replace the license and verify it with `mc license info`.
- Do not confuse the AIStor license with the S3 access key. The license authorizes AIStor; `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` authenticate users.

### Error: `Bind for 0.0.0.0:9000 failed: port is already allocated`

**Cause:** Another application or container already uses port 9000 or 9001. Docker documents this as a host port conflict. [6]

**Find the process using the ports:**

```powershell
netstat -aon | findstr LISTENING | findstr ":9000 :9001"
```

Check the PID:

```powershell
Get-Process -Id <PID>
```

**Solution A: stop the old AIStor container:**

```powershell
docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Ports}}"
docker stop <old-container-name>
```

**Solution B: use different host ports:**

```powershell
-p 19000:9000 `
-p 19001:9001
```

Then open `http://localhost:19001` for the Console and use `http://localhost:19000` as the S3 endpoint. The container ports remain 9000 and 9001.

### Error: the browser cannot open `localhost:9001`

**Cause:** The container is stopped, the Console port was not published, or the browser is using the wrong host port.

**Solution:**

```powershell
docker ps
docker port aistor
docker logs --tail 100 aistor
```

Make sure the run command includes:

```text
-p 9001:9001
```

Then try `http://127.0.0.1:9001`. If you changed the host port, use that host port instead.

### Error: the S3 API does not respond on port 9000

**Cause:** Port 9000 was not published, the container is unhealthy, or the application is using the Console port instead of the S3 port.

**Solution:**

```powershell
Invoke-WebRequest http://localhost:9000/minio/health/live
docker port aistor
```

Use port **9000** for S3 applications and port **9001** for the web Console.

### Error: PowerShell reports a parser error for the multi-line command

**Cause:** PowerShell uses the backtick character `` ` `` for line continuation. A trailing space after the backtick breaks continuation.

**Solution:**

- Ensure each backtick is the final character on its line.
- Or run the command as one line.
- Do not use PowerShell backticks in `cmd.exe`; use a single line there.

### Error: the container starts and immediately exits

**Cause:** The server command is invalid, the license cannot be read, a mount is wrong, or AIStor reports a startup validation error.

**Solution:**

```powershell
docker ps -a --filter name=aistor
docker logs aistor
docker inspect aistor --format '{{json .State}}'
```

Check the following:

- The final image name is present.
- The command is `server /mnt/data --license /minio.license --console-address ":9001"`.
- `C:\minio\data` is a directory.
- `C:\minio\minio.license` is a file.
- The root password is not empty.

### Error: data disappears after recreating the container

**Cause:** The container was run without a persistent data mount, or the mount points to a different Windows folder than expected.

**Solution:**

```powershell
docker inspect aistor
```

Confirm that the host source for the `/mnt/data` mount is `C:\minio\data`. Always use the same host data directory when recreating the container. Container removal deletes the container layer, not the data in a correctly configured bind mount.

### Error: very slow performance or high memory use on Windows

**Cause:** AIStor is running through Docker Desktop and WSL 2 virtualization. Using a Windows-mounted path can also be slower than using a Linux filesystem inside WSL for some workloads.

**Solution:**

- Give Docker Desktop adequate CPU and memory under **Settings > Resources**.
- Close unused containers and applications.
- Use a recent machine and adequate RAM.
- For local testing, consider placing development data inside a WSL 2 Linux filesystem if your workflow permits it.
- Do not treat a Windows Docker Desktop single-node setup as a production performance benchmark. MinIO identifies storage, controllers, and networking as major performance factors. [2]

### Error: TLS, proxy, certificate, or connection-reset errors while pulling the image

**Cause:** A corporate proxy, VPN, TLS inspection system, DNS issue, or a registry certificate problem can interrupt the pull.

**Solution:**

- Test network access from the host.
- Configure the proxy in Docker Desktop, not only in PowerShell.
- Temporarily test without the VPN if permitted by your organization.
- Ask the network administrator to allow the Quay registry.
- Do not disable TLS verification globally as a first fix.

### Error: the license works in the Windows binary but not in the container

**Cause:** The binary and container use different file paths. A Windows path such as `C:\minio\minio.license` does not exist inside the container.

**Solution:**

Use the host path only on the left side of the mount and the Linux container path on the right side:

```text
C:\minio\minio.license  ->  /minio.license
```

The server command must reference the container path:

```text
--license /minio.license
```

## 9. Optional license verification with `mc`

The AIStor Client (`mc`) can be downloaded for Windows from the official MinIO release location. The Windows documentation provides this PowerShell pattern:

```powershell
Invoke-WebRequest https://dl.min.io/aistor/mc/release/windows-amd64/mc.exe -OutFile C:\mc.exe
C:\mc.exe --version
```

Configure an alias using the S3 endpoint and the same credentials used for the container:

```powershell
C:\mc.exe alias set local http://localhost:9000 $AistorAdmin $AistorPassword
```

Check the license:

```powershell
C:\mc.exe license info local
```

If the deployment is not registered with SUBNET, license retrieval and automatic renewal may not be available. Follow the official license documentation for `mc license register`, `mc license update`, and manual license-file replacement. [5]

## 10. Safe reset procedure for a test installation

Use this only when you want to keep the host data but recreate the container:

```powershell
docker stop aistor
docker rm aistor
```

Then run the start command again.

To delete the test data as well, first make a backup, then remove the data folder:

```powershell
# Destructive: permanently deletes the local test objects
Remove-Item C:\minio\data -Recurse -Force
New-Item -ItemType Directory -Force C:\minio\data | Out-Null
```

Never run the destructive command on a folder containing data you need.

## 11. Quick checklist

Before asking for help, collect this information:

```powershell
docker version
docker info
docker image ls quay.io/minio/aistor/minio
docker ps -a --filter name=aistor
docker logs --tail 200 aistor
docker inspect aistor
wsl.exe -l -v
Test-Path C:\minio\data
Test-Path C:\minio\minio.license
```

Also record:

- Windows version.
- Docker Desktop version.
- Whether Docker is using Linux containers and WSL 2.
- The exact error text.
- Whether the failure occurs during image pull, container start, login, S3 access, or license validation.

## References

[1]: https://docs.min.io/aistor/installation/container/install/ "Deploy MinIO AIStor as a Container"

[2]: https://docs.min.io/aistor/installation/windows/ "Windows - MinIO AIStor Documentation"

[3]: https://docs.docker.com/desktop/features/wsl/ "Docker Desktop WSL 2 backend on Windows"

[4]: https://docs.docker.com/engine/storage/bind-mounts/ "Bind mounts - Docker Docs"

[5]: https://docs.min.io/aistor/operations/licenses/ "Licenses - MinIO AIStor Documentation"

[6]: https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/topics/ "Troubleshoot topics for Docker Desktop"

[7]: https://www.min.io/download/aistor-server "Download AIStor Server - MinIO"

[8]: https://docs.min.io/aistor/installation/windows/install/ "Deploy AIStor Server on Windows"

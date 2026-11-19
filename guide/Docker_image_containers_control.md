# Complete Docker Cleanup – Windows PowerShell

## 1. Purpose

This guide provides commands to completely clean up a Docker environment, including:

- All running and stopped containers
- All Docker images
- All Docker volumes
- Unused Docker networks
- Orphaned containers
- Docker build cache
- Unused Docker resources

**WARNING:** This operation is destructive. All Docker containers, images, volumes, and persistent data will be permanently deleted. This includes PostgreSQL databases, MinIO objects, Jenkins configurations, MLflow artifacts, and other application data stored in Docker volumes.

Make sure you have backed up any important data before proceeding.

## 2. Check Current Docker Resources

Before cleanup, inspect your current environment:

```powershell
docker ps -a
docker images -a
docker volume ls
docker network ls
docker system df
```

## 3. Stop All Running Containers

```powershell
$containers = docker ps -aq

if ($containers) {
    docker stop $containers
}
```

## 4. Remove All Containers

This removes running and stopped containers, including orphaned containers.

```powershell
$containers = docker ps -aq

if ($containers) {
    docker rm -f $containers
}
```

## 5. Remove All Docker Images

```powershell
$images = docker images -aq

if ($images) {
    docker rmi -f $images
}
```

## 6. Remove All Docker Volumes

**Important:** This permanently deletes persistent application data.

```powershell
$volumes = docker volume ls -q

if ($volumes) {
    docker volume rm -f $volumes
}
```

## 7. Remove Unused Docker Networks

```powershell
docker network prune -f
```

## 8. Remove All Docker Build Cache

```powershell
docker builder prune -a -f
```

## 9. Complete Docker System Cleanup

Run the following command to remove all remaining unused Docker resources:

```powershell
docker system prune -a --volumes -f
```

This removes:
- Unused containers
- Unused images
- Unused networks
- Unused volumes
- Build cache

## 10. Verify Docker Cleanup

Execute the following commands to verify the cleanup:

```powershell
docker ps -a
docker images -a
docker volume ls
docker network ls
docker system df
docker builder du
```

Expected results:

| Resource | Expected state |
|---|---|
| Containers | No containers |
| Images | No images |
| Volumes | No volumes |
| Networks | Only default Docker networks |
| Build cache | Empty or minimal |

## 11. Optional: Restart Docker Desktop

If needed, restart Docker Desktop to refresh the environment.

## 12. Complete Cleanup Script

Alternatively, execute the following complete script in PowerShell:

```powershell
Write-Host "=== Stopping all containers ==="

$containers = docker ps -aq
if ($containers) {
    docker stop $containers
}

Write-Host "=== Removing all containers ==="

$containers = docker ps -aq
if ($containers) {
    docker rm -f $containers
}

Write-Host "=== Removing all images ==="

$images = docker images -aq
if ($images) {
    docker rmi -f $images
}

Write-Host "=== Removing all volumes ==="

$volumes = docker volume ls -q
if ($volumes) {
    docker volume rm -f $volumes
}

Write-Host "=== Removing unused networks ==="

docker network prune -f

Write-Host "=== Removing all build cache ==="

docker builder prune -a -f

Write-Host "=== Final Docker system cleanup ==="

docker system prune -a --volumes -f

Write-Host "=== Docker Cleanup Completed ==="

Write-Host "=== Final Resource Verification ==="

docker ps -a
docker images -a
docker volume ls
docker network ls
docker system df
docker builder du
```
# Docker Cleanup Verification – Windows PowerShell

## 1. Purpose

This document explains how to verify that Docker has been successfully cleaned up after removing all containers, images, volumes, unused networks, and build cache.

The verification commands confirm that the Docker environment is ready for a fresh deployment.

## 2. Verify Docker Networks

Execute:

```powershell
docker network ls
```

Expected output:

```text
NETWORK ID     NAME      DRIVER    SCOPE
673eb1c4a392   bridge    bridge    local
7ea1e2263e7a   host      host      local
b001b0255894   none      null      local
```

**Explanation:**

Docker maintains three default networks:

| Network | Description |
|---|---|
| `bridge` | Default network for container communication |
| `host` | Allows containers to share the host network |
| `none` | Disables container networking |

**Expected result:** These three default networks are normal and should remain available. Their presence does not indicate incomplete cleanup.

## 3. Verify Docker Disk Usage

Execute:

```powershell
docker system df
```

Expected output:

```text
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          0         0          0B        0B
Containers      0         0          0B        0B
Local Volumes   0         0          0B        0B
Build Cache     0         0          0B        0B
```

**Explanation:**

| Resource | Description | Expected |
|---|---|---|
| Images | Downloaded and locally built Docker images | 0 |
| Containers | Running and stopped containers | 0 |
| Local Volumes | Docker-managed persistent storage | 0 |
| Build Cache | Cached Docker build layers | 0B |

Additional columns:

- **TOTAL:** Total number of resources.
- **ACTIVE:** Number of resources currently in use.
- **SIZE:** Disk space consumed.
- **RECLAIMABLE:** Disk space that Docker can potentially recover.

**Expected result:** All resource counts and disk usage should be zero.

## 4. Verify Docker Build Cache

Execute:

```powershell
docker builder du
```

Expected output:

```text
ID        RECLAIMABLE   SIZE      LAST ACCESSED
Reclaimable:    0B
Total:          0B
```

**Explanation:**

Docker build cache stores intermediate layers and previously executed build operations.

It can include:

- Cached base image layers.
- Intermediate Dockerfile build layers.
- Cached dependency installation steps.
- Cached application compilation steps.

**Expected result:** 

- Reclaimable: 0B
- Total: 0B

This confirms that Docker's build cache is empty.

## 5. Final Docker Cleanup Verification

| Component | Expected status | Result |
|---|---|---|
| Running containers | 0 | Clean |
| Stopped containers | 0 | Clean |
| Docker images | 0 | Clean |
| Docker volumes | 0 | Clean |
| Build cache | 0B | Clean |
| Unused networks | No custom unused networks | Clean |
| Default networks | 3 | Normal |

## 6. Conclusion

The verification confirms that the Docker environment has been successfully cleaned.

All Docker-managed application resources have been removed:

- Containers and orphaned containers.
- Docker images.
- Docker volumes and associated persistent application data.
- Unused Docker networks.
- Docker build cache.

The three default Docker networks (`bridge`, `host`, and `none`) remain available, as expected.

**The Docker environment is ready for fresh deployments.**

New Docker images, containers, volumes, and networks can now be created when deploying applications such as:

- Jenkins
- MinIO / AIStor
- PostgreSQL
- MLflow
- CrewAI
- FastAPI

**Note:** This verification covers Docker-managed resources. It does not confirm that all Docker Desktop internal files, configuration files, or data stored outside Docker volumes have been deleted.




---

**Note:** This script removes Docker-managed resources, not Docker Desktop itself, local project source code, or files stored outside Docker-managed volumes. Docker Desktop may retain some internal or default resources. For a completely fresh Docker environment, additional Docker Desktop data reset may be required.
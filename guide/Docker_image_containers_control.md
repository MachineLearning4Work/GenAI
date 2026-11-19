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

Note : 

```powershell
docker network ls
```
 ----------->
 Lists all Docker networks.

Your output:
Network,	Purpose
bridge,	Default network used by containers for communication
host,	Allows containers to share the host network
none,	Disables container networking

(base) PS C:\Users\....> docker network ls
NETWORK ID     NAME      DRIVER    SCOPE
673eb....2   bridge    bridge    local
7ea1e2.....7a   host      host      local
b001b.....4   none      null      local



Expected result
 These three default networks are normal. Docker maintains them automatically. You should not try to delete them.

---

**Note:** This script removes Docker-managed resources, not Docker Desktop itself, local project source code, or files stored outside Docker-managed volumes. Docker Desktop may retain some internal or default resources. For a completely fresh Docker environment, additional Docker Desktop data reset may be required.
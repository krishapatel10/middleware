# Troubleshooting GitHub Actions Self-Hosted Runner

## Docker systemd/cgroup Error

If you see this error:
```
Failed to activate service 'org.freedesktop.systemd1': timed out
```

This is a systemd/cgroup configuration issue on your self-hosted runner.

## Solutions

### Option 1: Restart Docker and systemd (Quick Fix)

On your self-hosted runner machine, run:

```bash
sudo systemctl restart docker
sudo systemctl daemon-reload
```

### Option 2: Fix Docker systemd Integration

1. Check Docker service status:
```bash
sudo systemctl status docker
```

2. Check if Docker can access systemd:
```bash
sudo journalctl -u docker.service --no-pager -n 50
```

3. Restart Docker with proper systemd integration:
```bash
sudo systemctl stop docker
sudo systemctl start docker
```

### Option 3: Configure Docker to use cgroupfs (Workaround)

Edit Docker daemon configuration:

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "exec-opts": ["native.cgroupdriver=cgroupfs"]
}
EOF
sudo systemctl restart docker
```

### Option 4: Check Runner Permissions

Ensure the GitHub Actions runner user has proper permissions:

```bash
# Add runner user to docker group
sudo usermod -aG docker $USER
# Or if runner runs as specific user:
sudo usermod -aG docker <runner-user>

# Restart runner service
sudo systemctl restart actions.runner.*
```

### Option 5: Check systemd and cgroup Status

```bash
# Check systemd status
systemctl status

# Check cgroup version
stat -fc %T /sys/fs/cgroup/

# If using cgroup v2, you may need:
sudo mkdir -p /sys/fs/cgroup/systemd
sudo mount -t cgroup2 none /sys/fs/cgroup/systemd
```

## Verify Fix

After applying a fix, test Docker:

```bash
docker run hello-world
```

If this works, your GitHub Actions workflow should work too.

## Alternative: Use Docker without systemd

If systemd continues to cause issues, you can configure Docker to run without systemd integration, though this is less ideal for production.


# CI/CD Deployment Pipeline to Raspberry Pi via GitHub Actions Self-Hosted Runner

* **Date:** 2026-06-11
* **Status:** Approved
* **Authors:** Antigravity (Gemini 3.5 Flash)

---

## 1. Goal & Requirements
Implement a continuous integration and continuous deployment (CI/CD) pipeline for the `stock-tracker` project. When changes are pushed or merged into the `main` branch of the GitHub repository (`https://github.com/jqrsantos/stock-tracker-gemipi.git`), the application running on the Raspberry Pi must automatically update.

### Key Constraints:
1. **Security:** The Raspberry Pi must not expose any inbound ports (like SSH) to the public internet.
2. **Build Location:** Docker images must be built on the Pi itself to keep the workflow simple (avoiding registry credentials/configuration and multi-platform compilation).
3. **Trigger:** Automatic deployment on every commit/merge to `main`.

---

## 2. Selected Architecture: Host-Level Self-Hosted Runner (Approach 1)

Instead of exposing the Pi to the internet and SSHing into it from GitHub, the Raspberry Pi will run a lightweight GitHub Actions Runner daemon. This runner polls GitHub for new jobs over a secure outbound connection (HTTPS). 

When a workflow runs, the runner:
1. Navigates to `/home/joaosantos/stock-tracker`.
2. Pulls the latest code using `git pull`.
3. Runs `docker compose up -d --build`.

```
+-------------------+                    +-------------------------+
|   GitHub Repo     |                    |  Raspberry Pi (Local)   |
|                   |                    |                         |
|  [Push/Merge]     |                    |  +-------------------+  |
|         |         |                    |  | GHA Runner Agent  |  |
|         v         |   Polls (Outbound) |  |   (Background)    |  |
|  Triggers Job     |<======================|                   |  |
|                   |                    |  +---------+---------+  |
+-------------------+                    |            |            |
                                         |            v (Local Commands)
                                         |   - cd /home/joaosantos/...
                                         |   - git pull origin main
                                         |   - docker compose up -d
                                         +-------------------------+
```

---

## 3. GitHub Actions Workflow Configuration
We will create a file `.github/workflows/deploy.yml` in the repository:

```yaml
name: Deploy Stock Tracker

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: self-hosted
    steps:
      - name: Deploy to Raspberry Pi
        run: |
          cd /home/joaosantos/stock-tracker
          git pull origin main
          docker compose up -d --build
```

---

## 4. Raspberry Pi Deployment Agent Instructions (Abstract)
The agent on the Raspberry Pi must complete the following configuration:
1. Ensure the user (e.g., `joaosantos`) is in the `docker` group to run Docker without `sudo`.
2. Verify that non-interactive `git pull` from the repository works without prompting for username/password.
3. Download the GitHub Actions runner package matching the CPU architecture (ARM or ARM64).
4. Register the runner using the repository token from GitHub Settings.
5. Install and start the runner as a background `systemd` service.

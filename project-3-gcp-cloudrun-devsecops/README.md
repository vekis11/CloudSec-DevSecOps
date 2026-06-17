# Project 3: GCP Cloud Run DevSecOps Pipeline

Deploy a **Node.js Express** API on **Google Cloud Run** with **Artifact Registry**, authenticated via **Workload Identity Federation** (no GCP service account keys). The GitHub Actions pipeline runs **Semgrep**, **ESLint security**, **Trivy**, **npm audit** (SCA), **Checkov**, and **tfsec** (IaC) before every deployment.

## Architecture

```
Developer → GitHub PR/Push
    │
    ├─ Gitleaks (secrets)
    ├─ Semgrep + ESLint (SAST)
    ├─ Trivy + npm audit (SCA)
    ├─ Checkov + tfsec (IaC)
    ├─ Unit tests
    ├─ Trivy (container)
    │
    └─ Build → Artifact Registry → Cloud Run
```

| Component | Technology |
|-----------|------------|
| Cloud | Google Cloud Platform |
| Compute | Cloud Run (v2) |
| Registry | Artifact Registry |
| IaC | Terraform |
| CI/CD | GitHub Actions + WIF |
| SAST | Semgrep, ESLint-plugin-security |
| SCA | Trivy, npm audit |
| IaC Scan | Checkov, tfsec |
| Secrets | Gitleaks |
| Auth to GCP | Workload Identity Federation |

## Prerequisites

| Tool | Install |
|------|---------|
| Google Cloud SDK (`gcloud`) | [Install guide](https://cloud.google.com/sdk/docs/install) |
| Terraform | >= 1.5 |
| Docker Desktop | latest |
| Node.js | 20+ (local testing) |

### GCP account setup

1. Create a GCP project at [console.cloud.google.com](https://console.cloud.google.com).
2. Enable billing on the project.
3. Authenticate:
   ```powershell
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```
4. Verify:
   ```powershell
   gcloud projects describe YOUR_PROJECT_ID
   ```

Estimated cost: **$0–10/month** with scale-to-zero Cloud Run (min instances = 0).

---

## Step 1: Create GitHub repository

Use a monorepo containing all three projects, or a dedicated repo. Update `github_repo` in Terraform to match.

```powershell
cd "C:\Users\vekis\Desktop\CICD\CloudSec & DevSecOps"
git init
git add .
git commit -m "Add DevSecOps lab projects"
git remote add origin https://github.com/YOUR_USERNAME/devsecops-labs.git
git push -u origin main
```

---

## Step 2: Configure Terraform variables

```powershell
cd project-3-gcp-cloudrun-devsecops\terraform
copy terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
gcp_project_id = "your-actual-project-id"
gcp_region     = "us-central1"
github_org     = "YOUR_GITHUB_USERNAME"
github_repo    = "devsecops-labs"
project_name   = "cloudrun-devsecops"
environment    = "dev"
```

---

## Step 3: Deploy GCP infrastructure

```powershell
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### Resources created

- Required GCP APIs (Run, Artifact Registry, IAM, IAM Credentials)
- Artifact Registry Docker repository
- Cloud Run v2 service with health/liveness probes
- Service accounts for Cloud Run runtime and GitHub Actions
- Workload Identity Pool + OIDC provider for GitHub
- IAM bindings for keyless CI/CD

Save outputs:

```powershell
terraform output
```

---

## Step 4: Bootstrap the first container image

Cloud Run needs an image in Artifact Registry before the service becomes healthy.

```powershell
$PROJECT_ID = "your-gcp-project-id"
$REGION = "us-central1"
$REPO = "cloudrun-devsecops-repo"
$IMAGE = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/app:latest"

gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet

docker build -t $IMAGE project-3-gcp-cloudrun-devsecops\app
docker push $IMAGE

gcloud run services update cloudrun-devsecops-service `
  --image $IMAGE `
  --region $REGION `
  --project $PROJECT_ID
```

Verify:

```powershell
$URL = terraform output -raw cloud_run_url
curl "$URL/health"
```

---

## Step 5: Configure GitHub Actions

**Settings → Secrets and variables → Actions**

### Secrets

| Name | Value |
|------|-------|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `terraform output -raw workload_identity_provider` |
| `GCP_SERVICE_ACCOUNT` | `terraform output -raw github_actions_service_account` |

### Variables

| Name | Value |
|------|-------|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_REGION` | `us-central1` |
| `ARTIFACT_REGISTRY` | `terraform output -raw artifact_registry_url` |

Example `ARTIFACT_REGISTRY` value:
`us-central1-docker.pkg.dev/my-project/cloudrun-devsecops-repo`

---

## Step 6: Run the CI/CD pipeline

### On pull request

```powershell
git checkout -b fix/remove-debug-token
# Edit server.js — remove DEBUG_TOKEN
git add .
git commit -m "fix: remove hardcoded debug token"
git push -u origin fix/remove-debug-token
```

Open a PR. Jobs that run:

1. Gitleaks
2. Semgrep + ESLint security
3. npm audit + Trivy SCA
4. Checkov + tfsec on Terraform
5. Node.js unit tests
6. Trivy container scan

### On merge to main

The deploy job:

1. Authenticates via Workload Identity Federation
2. Builds and pushes image to Artifact Registry (SHA + latest tags)
3. Updates Cloud Run service with new image
4. Smoke tests `/health`

---

## Step 7: Practice security findings

| Finding | Tool | Location |
|---------|------|----------|
| Hardcoded debug token | Gitleaks, Semgrep | `app/server.js` |
| Prototype pollution | Semgrep, ESLint | `app/server.js` |
| Outdated express CVEs | npm audit, Trivy | `app/package.json` |
| Public Cloud Run invoker | Checkov/tfsec | `terraform/cloudrun.tf` |

### Fix exercises

1. Remove `DEBUG_TOKEN` and use Secret Manager
2. Remove `__proto__` handling block
3. Upgrade `express` to latest patched version
4. Replace `allUsers` invoker with IAM-authenticated access

---

## Step 8: Local security scanning

```powershell
cd project-3-gcp-cloudrun-devsecops\app
npm install
npm audit
npm test

# Semgrep
semgrep --config p/javascript --config ../security/semgrep-rules.yml .

# Trivy
trivy fs --scanners vuln .

# Checkov
checkov -d ../terraform/

# tfsec
docker run --rm -v ${PWD}/../terraform:/src aquasec/tfsec /src
```

---

## Step 9: Monitor Cloud Run

```powershell
# Service status
gcloud run services describe cloudrun-devsecops-service --region us-central1

# Logs
gcloud run services logs read cloudrun-devsecops-service --region us-central1 --limit 50

# Metrics in Console
# https://console.cloud.google.com/run
```

---

## Step 10: Tear down

```powershell
cd project-3-gcp-cloudrun-devsecops\terraform
terraform destroy
```

Also delete Artifact Registry images if any remain after destroy.

---

## Workload Identity Federation explained

Traditional CI/CD used JSON key files for GCP service accounts — a security risk if leaked. WIF allows GitHub Actions to exchange an OIDC token for short-lived GCP credentials.

```
GitHub Actions OIDC token
    → Workload Identity Pool Provider (validates repo)
    → Impersonate github-actions@... service account
    → Push to Artifact Registry + deploy Cloud Run
```

The Terraform `attribute_condition` restricts access to your exact repository:
`assertion.repository == 'YOUR_ORG/YOUR_REPO'`

---

## Troubleshooting

### "Permission denied" pushing to Artifact Registry

- Verify `roles/artifactregistry.writer` on the GitHub Actions SA
- Run `gcloud auth configure-docker` in the deploy job (already included)

### WIF authentication fails

- `GCP_WORKLOAD_IDENTITY_PROVIDER` must be the **full** resource name:
  `projects/123/locations/global/workloadIdentityPools/.../providers/github-provider`
- `github_org` and `github_repo` in Terraform must match exactly

### npm audit fails on express 4.18.2

- Upgrade express in `package.json` or pin overrides
- For learning only, use `npm audit --audit-level=critical`

### Cloud Run 403 on smoke test

- Service may need a minute after deploy
- Verify `google_cloud_run_v2_service_iam_member.public_invoker` exists

---

## File structure

```
project-3-gcp-cloudrun-devsecops/
├── app/
│   ├── server.js
│   ├── package.json
│   ├── Dockerfile
│   └── test/health.test.js
├── security/
│   └── semgrep-rules.yml
└── terraform/
    ├── main.tf
    ├── apis.tf
    ├── cloudrun.tf
    ├── wif.tf
    ├── variables.tf
    ├── outputs.tf
    └── terraform.tfvars.example
```

Workflows live at the **repository root**:
`.github/workflows/project-3-gcp-cloudrun-devsecops.yml`

# Project 1: AWS ECS Fargate DevSecOps Pipeline

Deploy a containerized Flask API on **Amazon ECS Fargate** with a full **GitHub Actions** CI/CD pipeline that runs **SAST**, **SCA**, **IaC scanning**, **secret detection**, and **container scanning** before every deployment.

## Architecture

```
Developer → GitHub PR/Push
    │
    ├─ Gitleaks (secrets)
    ├─ Semgrep (SAST)
    ├─ Trivy (SCA + container)
    ├─ Checkov + tfsec (IaC)
    │
    └─ Build → ECR → ECS Fargate (behind ALB)
```

| Component | Technology |
|-----------|------------|
| Cloud | AWS |
| Compute | ECS Fargate |
| Registry | Amazon ECR |
| Load Balancer | Application Load Balancer |
| IaC | Terraform |
| CI/CD | GitHub Actions |
| SAST | Semgrep |
| SCA | Trivy |
| IaC Scan | Checkov, tfsec |
| Secrets | Gitleaks |
| Auth to AWS | GitHub OIDC (no long-lived keys) |

## Prerequisites

Install these tools on your workstation before starting:

| Tool | Version | Install |
|------|---------|---------|
| AWS CLI | v2+ | [Install guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) |
| Terraform | >= 1.5 | [Install guide](https://developer.hashicorp.com/terraform/install) |
| Docker Desktop | latest | [Install guide](https://docs.docker.com/get-docker/) |
| Git | latest | [Install guide](https://git-scm.com/downloads) |
| Python | 3.12+ | Optional, for local app testing |

### AWS account setup

1. Create or use an AWS account with **AdministratorAccess** (for learning labs only).
2. Configure AWS CLI:
   ```powershell
   aws configure
   # Enter: Access Key ID, Secret Access Key, region (e.g. us-east-1), output json
   ```
3. Verify:
   ```powershell
   aws sts get-caller-identity
   ```

### Estimated AWS cost

Running this lab 24/7 costs roughly **$30–50/month** (NAT Gateway, ALB, Fargate). Run `terraform destroy` when finished to avoid charges.

---

## Step 1: Fork or clone this repository

```powershell
cd "C:\Users\vekis\Desktop\CICD\CloudSec & DevSecOps"
git init
git add .
git commit -m "Initial DevSecOps lab projects"
```

Create a **new GitHub repository** named `ecs-devsecops-demo` (or any name — update Terraform variables accordingly).

```powershell
git remote add origin https://github.com/YOUR_USERNAME/ecs-devsecops-demo.git
git branch -M main
git push -u origin main
```

---

## Step 2: Configure Terraform variables

```powershell
cd project-1-aws-ecs-devsecops\terraform
copy terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
github_org   = "YOUR_GITHUB_USERNAME"
github_repo  = "ecs-devsecops-demo"
aws_region   = "us-east-1"
environment  = "dev"
project_name = "ecs-devsecops"
```

Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username or organization.

---

## Step 3: Deploy AWS infrastructure with Terraform

```powershell
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

Type `yes` when prompted.

### What Terraform creates

- VPC with public/private subnets across 2 AZs
- NAT Gateway for private subnet egress
- Application Load Balancer (HTTP on port 80)
- ECR repository with scan-on-push enabled
- ECS Fargate cluster, task definition, and service
- IAM OIDC provider for GitHub Actions
- IAM role for keyless CI/CD deployment

### Save Terraform outputs

```powershell
terraform output
```

Copy these values — you will need them for GitHub:

| Output | GitHub usage |
|--------|--------------|
| `github_actions_role_arn` | Repository secret `AWS_ROLE_ARN` |
| `aws_region` | Repository variable `AWS_REGION` |
| `application_url` | Verify deployment after CI/CD |

---

## Step 4: Configure GitHub repository secrets and variables

In your GitHub repo: **Settings → Secrets and variables → Actions**

### Secrets

| Name | Value |
|------|-------|
| `AWS_ROLE_ARN` | Output from `terraform output github_actions_role_arn` |

### Variables (optional)

| Name | Value |
|------|-------|
| `AWS_REGION` | `us-east-1` |

No `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` is required — OIDC handles authentication.

---

## Step 5: Push an initial container image (bootstrap)

ECS needs at least one image in ECR before the service stabilizes. The first GitHub Actions run on `main` will build and push, but you can bootstrap locally:

```powershell
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$REGION = "us-east-1"
$ECR_URL = "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/ecs-devsecops-app"

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

docker build -t $ECR_URL:latest project-1-aws-ecs-devsecops\app
docker push $ECR_URL:latest

aws ecs update-service --cluster ecs-devsecops-cluster --service ecs-devsecops-service --force-new-deployment
```

---

## Step 6: Trigger the DevSecOps pipeline

### On pull request (security gates only)

```powershell
git checkout -b feature/test-security-scan
# Make a small change
echo "# test" >> project-1-aws-ecs-devsecops\app\README.md
git add .
git commit -m "test: trigger security scans"
git push -u origin feature/test-security-scan
```

Open a PR on GitHub. The pipeline runs:

1. **Gitleaks** — scans git history for secrets
2. **Semgrep** — SAST on Python/Flask code
3. **Trivy SCA** — dependency vulnerabilities in `requirements.txt`
4. **Checkov + tfsec** — Terraform misconfigurations
5. **Trivy container** — image vulnerabilities and Dockerfile issues

Deployment does **not** run on PRs.

### On merge to main (full deploy)

Merge the PR. The `build-and-deploy` job:

1. Assumes AWS role via OIDC
2. Builds and pushes image to ECR (tagged with commit SHA)
3. Updates ECS task definition
4. Rolls out new tasks with zero-downtime deployment

---

## Step 7: Verify the deployment

```powershell
terraform output application_url
# Example: http://ecs-devsecops-alb-123456789.us-east-1.elb.amazonaws.com/health

curl (terraform output -raw application_url)
```

Expected response:

```json
{"status":"healthy","service":"ecs-devsecops-demo"}
```

Check ECS:

```powershell
aws ecs describe-services --cluster ecs-devsecops-cluster --services ecs-devsecops-service
```

Check CloudWatch logs:

```powershell
aws logs tail /ecs/ecs-devsecops --follow
```

---

## Step 8: Practice security findings

The sample app includes **intentional** issues for learning:

| Finding | Tool | Location |
|---------|------|----------|
| Hardcoded API key | Gitleaks, Semgrep | `app/app.py` |
| `shell=True` subprocess | Semgrep | `app/app.py` |
| Outdated `requests` CVEs | Trivy SCA | `requirements.txt` |
| Public ALB (no HTTPS) | Checkov/tfsec | `terraform/alb.tf` |

### Fix exercise

1. Remove `DEMO_API_KEY` and use AWS Secrets Manager or SSM Parameter Store
2. Remove the unsafe `subprocess` block
3. Pin and upgrade dependencies: `pip install --upgrade requests`
4. Add ACM certificate + HTTPS listener (advanced)

Re-push and confirm scans pass.

---

## Step 9: Local security scanning (optional)

Run the same tools locally before pushing:

```powershell
# Semgrep
pip install semgrep
semgrep --config p/python --config security/semgrep-rules.yml app/

# Trivy SCA
trivy fs --scanners vuln app/

# Checkov
pip install checkov
checkov -d terraform/

# tfsec
docker run --rm -v ${PWD}/terraform:/src aquasec/tfsec /src

# Gitleaks
docker run -v ${PWD}:/path zricethezav/gitleaks:latest detect --source /path -v
```

---

## Step 10: Tear down infrastructure

```powershell
cd project-1-aws-ecs-devsecops\terraform
terraform destroy
```

Confirm with `yes`. Verify in AWS Console that ECR images are deleted (lifecycle policy keeps last 10).

---

## Troubleshooting

### GitHub Actions: "Not authorized to perform sts:AssumeRoleWithWebIdentity"

- Verify `github_org` and `github_repo` in `terraform.tfvars` match your repository exactly (case-sensitive).
- Ensure the workflow has `permissions: id-token: write`.

### ECS tasks fail health checks

- Check CloudWatch log group `/ecs/ecs-devsecops`
- Ensure an image exists in ECR (`:latest` or the SHA tag from CI)
- Verify security groups allow ALB → ECS on port 8080

### Trivy fails on known CVEs in base image

- Update the Dockerfile base image tag
- Or temporarily set `exit-code: 0` in the workflow for learning (not recommended for production)

### NAT Gateway costs

- For a cheaper lab, switch ECS tasks to public subnets with `assign_public_ip = true` and remove NAT (less secure, fine for sandbox).

---

## File structure

```
project-1-aws-ecs-devsecops/
├── app/
│   ├── app.py              # Sample Flask API
│   ├── Dockerfile          # Hardened container image
│   └── requirements.txt    # Python dependencies (SCA target)
├── security/
│   └── semgrep-rules.yml   # Custom SAST rules
├── terraform/
│   ├── main.tf
│   ├── vpc.tf
│   ├── alb.tf
│   ├── ecs.tf
│   ├── github_oidc.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── terraform.tfvars.example
└── .github/workflows/
    └── devsecops-pipeline.yml   # Copy also exists at repo root: .github/workflows/project-1-ecs-devsecops.yml
```

> GitHub Actions reads workflows from the **repository root** `.github/workflows/` directory. Use `project-1-ecs-devsecops.yml` at the monorepo root when running all projects from one repo.

---

## Next steps

- Add **HTTPS** with ACM and Route 53
- Store secrets in **AWS Secrets Manager**
- Enable **AWS WAF** on the ALB
- Add **OWASP ZAP** DAST stage post-deploy
- Proceed to **Project 2** (AWS Serverless) in the parent README

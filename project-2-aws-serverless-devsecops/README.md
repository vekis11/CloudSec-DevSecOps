# Project 2: AWS Serverless DevSecOps Pipeline

Deploy a **Python Lambda** API behind **API Gateway** with **DynamoDB** storage. The GitHub Actions pipeline runs **Bandit** and **Semgrep** (SAST), **Trivy** and **pip-audit** (SCA), **Checkov**, **tfsec**, and **KICS** (IaC), plus **Gitleaks** (secrets) before every deployment.

## Architecture

```
Developer → GitHub PR/Push
    │
    ├─ Gitleaks (secrets)
    ├─ Bandit + Semgrep (SAST)
    ├─ Trivy + pip-audit (SCA)
    ├─ Checkov + tfsec + KICS (IaC)
    │
    └─ Zip package → S3 → Lambda update → API Gateway
```

| Component | Technology |
|-----------|------------|
| Cloud | AWS |
| Compute | AWS Lambda (Python 3.12) |
| API | API Gateway REST |
| Database | DynamoDB (on-demand) |
| Artifacts | S3 (versioned, encrypted) |
| IaC | Terraform |
| CI/CD | GitHub Actions + OIDC |
| SAST | Bandit, Semgrep |
| SCA | Trivy, pip-audit |
| IaC Scan | Checkov, tfsec, KICS |
| Secrets | Gitleaks |

## Prerequisites

Same as Project 1, plus:

```powershell
pip install bandit pip-audit
```

Estimated cost: **$5–15/month** for light usage (Lambda free tier covers most lab traffic). DynamoDB on-demand and API Gateway have minimal charges.

---

## Step 1: Create GitHub repository

Create a repo named `serverless-devsecops-demo` (or update `terraform.tfvars`).

Push this project's files:

```powershell
cd "C:\Users\vekis\Desktop\CICD\CloudSec & DevSecOps"
git add project-2-aws-serverless-devsecops
git commit -m "Add serverless DevSecOps project"
git push
```

---

## Step 2: Configure Terraform

```powershell
cd project-2-aws-serverless-devsecops\terraform
copy terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your GitHub username and repo name.

---

## Step 3: Deploy infrastructure

```powershell
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### Resources created

- DynamoDB table `serverless-devsecops-items` (encrypted, PITR enabled)
- S3 bucket for Lambda deployment artifacts
- Lambda function with IAM least-privilege DynamoDB access
- API Gateway REST API with `{proxy+}` integration
- CloudWatch log group for Lambda
- GitHub OIDC IAM role for deployments

Save outputs:

```powershell
terraform output api_gateway_url
terraform output github_actions_role_arn
terraform output s3_artifacts_bucket
```

---

## Step 4: Configure GitHub Actions

**Settings → Secrets and variables → Actions**

### Secrets

| Name | Value |
|------|-------|
| `AWS_ROLE_ARN_SERVERLESS` | `terraform output -raw github_actions_role_arn` |

### Variables

| Name | Value |
|------|-------|
| `AWS_REGION` | `us-east-1` |
| `S3_ARTIFACTS_BUCKET` | Output `s3_artifacts_bucket` |

> Use a **different secret name** (`AWS_ROLE_ARN_SERVERLESS`) if you run both AWS projects in the same monorepo.

---

## Step 5: Initial Lambda deployment

Terraform deploys Lambda with a zip built at apply time. Verify:

```powershell
$URL = terraform output -raw api_gateway_url
curl $URL
```

Expected:

```json
{"status":"healthy","service":"serverless-devsecops"}
```

Test creating an item:

```powershell
$BASE = $URL -replace '/health$',''
curl -X POST "$BASE/items" -H "Content-Type: application/json" -d '{"name":"test-item"}'
curl "$BASE/items"
```

---

## Step 6: Run the CI/CD pipeline

### Pull request (security only)

```powershell
git checkout -b fix/remove-eval
# Edit lambda_function.py to remove eval usage
git add .
git commit -m "fix: remove unsafe eval"
git push -u origin fix/remove-eval
```

Open a PR. All security jobs must pass before merge.

### Merge to main (deploy)

After merge, the pipeline:

1. Installs Python dependencies into a `package/` directory
2. Zips the deployment package
3. Uploads to S3 with commit SHA in the key
4. Calls `aws lambda update-function-code`
5. Runs a smoke test against `/health`

---

## Step 7: Understand each security tool

### Bandit (Python SAST)

Flags dangerous patterns like `eval()`, hardcoded passwords, SQL injection risks.

```powershell
bandit -r app/ -ll
```

The sample `eval()` in `lambda_function.py` triggers **B307**.

### Semgrep (multi-language SAST)

Uses community rulesets (`p/python`).

```powershell
semgrep --config p/python app/
```

### pip-audit (Python SCA)

Checks PyPI packages against known CVE databases.

```powershell
pip-audit -r app/requirements.txt
```

### Trivy (SCA)

Broader vulnerability and license scanning.

### Checkov + tfsec + KICS (IaC)

Three complementary Terraform scanners:

| Tool | Focus |
|------|-------|
| Checkov | Policy-as-code, CIS benchmarks |
| tfsec | AWS-specific misconfigurations |
| KICS | 2000+ queries across IaC types |

```powershell
checkov -d terraform/
docker run --rm -v ${PWD}/terraform:/src aquasec/tfsec /src
docker run --rm -v ${PWD}/terraform:/path checkmarx/kics scan -p /path
```

---

## Step 8: Practice exercises

1. **Fix Bandit finding**: Remove `eval()` and use safe parsing
2. **Enable API Gateway auth**: Add IAM or Cognito authorizer in Terraform
3. **Add WAF**: Attach AWS WAF to API Gateway stage
4. **Lambda layers**: Move dependencies to a Lambda layer for faster deploys
5. **Add SAST gate**: Fail the pipeline if Bandit finds HIGH severity issues

---

## Step 9: Monitor and debug

```powershell
# Lambda logs
aws logs tail /aws/lambda/serverless-devsecops-api --follow

# Recent invocations
aws lambda get-function --function-name serverless-devsecops-api

# DynamoDB items
aws dynamodb scan --table-name serverless-devsecops-items
```

---

## Step 10: Tear down

```powershell
cd project-2-aws-serverless-devsecops\terraform
terraform destroy
```

---

## Troubleshooting

### API Gateway returns 502

- Check Lambda logs for import errors (missing `boto3` in zip)
- Ensure `package/` step in CI includes all dependencies

### OIDC assume role fails

- Match `github_org` / `github_repo` exactly in Terraform
- Use secret `AWS_ROLE_ARN_SERVERLESS` (not the ECS project's secret)

### KICS fails the build

- Review `kics-results.json` artifact
- For learning, set `ignore_on_exit: results` (already configured — fails only on errors)

---

## File structure

```
project-2-aws-serverless-devsecops/
├── app/
│   ├── lambda_function.py
│   └── requirements.txt
├── terraform/
│   ├── main.tf
│   ├── dynamodb.tf
│   ├── lambda.tf
│   ├── apigateway.tf
│   ├── github_oidc.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── terraform.tfvars.example
└── .github/workflows/
    └── devsecops-pipeline.yml   # Copy also exists at repo root: .github/workflows/project-2-serverless-devsecops.yml
```

> GitHub Actions reads workflows from the **repository root** `.github/workflows/` directory. Use `project-2-serverless-devsecops.yml` at the monorepo root when running all projects from one repo.

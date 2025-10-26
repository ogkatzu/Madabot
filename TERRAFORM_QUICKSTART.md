# Terraform Quick Start Guide

## 🚀 Initial Setup (One-Time)

### 1. Install Prerequisites

```bash
# Install Terraform
brew install terraform  # macOS
# or download from https://www.terraform.io/downloads

# Install AWS CLI
brew install awscli
aws configure
```

### 2. Create Backend Infrastructure

```bash
# Use the Makefile helper
make setup-backend ENV=dev

# Or manually:
aws s3 mb s3://mcp-first-responder-terraform-state-dev --region us-east-1
aws s3api put-bucket-versioning \
  --bucket mcp-first-responder-terraform-state-dev \
  --versioning-configuration Status=Enabled

aws dynamodb create-table \
  --table-name mcp-first-responder-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### 3. Set Environment Variables

```bash
# Choose your AI provider in terraform/environments/dev.tfvars:
# ai_provider = "google"     # For Google Gemini (recommended for cost)
# ai_provider = "anthropic"  # For Anthropic Claude

# For Google Gemini (default):
export TF_VAR_google_api_key="YOUR-GOOGLE-API-KEY"

# OR for Anthropic Claude:
# export TF_VAR_anthropic_api_key="sk-ant-api03-YOUR-KEY"

# Required for all:
export TF_VAR_slack_webhook_url="YOUR-SLACK-WEBHOOK-URL"
export TF_VAR_owner_email="your-email@example.com"

# Optional (for Jira integration):
export TF_VAR_jira_api_token="YOUR-JIRA-TOKEN"
```

**Note**: See [GEMINI_SETUP.md](GEMINI_SETUP.md) for detailed Gemini configuration.

## 📦 Development Workflow

### Using Makefile (Recommended)

```bash
# Initialize for dev environment
make init ENV=dev

# Plan changes
make plan ENV=dev

# Apply changes
make apply ENV=dev

# View outputs
make output

# Tail logs
make logs-analyzer

# Full deployment (init + validate + plan + apply)
make deploy ENV=dev
```

### Using Terraform CLI Directly

```bash
cd terraform

# Initialize
terraform init -backend-config=environments/dev-backend.tfvars

# Plan
terraform plan -var-file=environments/dev.tfvars

# Apply
terraform apply -var-file=environments/dev.tfvars

# Output
terraform output
```

## 🏗️ Multi-Environment Deployment

### Development

```bash
make dev
# or
cd terraform
terraform init -backend-config=environments/dev-backend.tfvars
terraform apply -var-file=environments/dev.tfvars
```

### Staging

```bash
make staging
# or
cd terraform
terraform init -backend-config=environments/staging-backend.tfvars -reconfigure
terraform apply -var-file=environments/staging.tfvars
```

### Production

```bash
make prod
# or
cd terraform
terraform init -backend-config=environments/prod-backend.tfvars -reconfigure
terraform apply -var-file=environments/prod.tfvars
```

## 🧪 Testing & Monitoring

### Test Lambda Functions

```bash
# Test ingestor
make test-ingestor

# View logs
make logs-ingestor
make logs-analyzer
make logs-notifier

# Check queues
make check-queue
make check-dlq
```

### Manual Testing

```bash
# Invoke Lambda directly
aws lambda invoke \
  --function-name $(cd terraform && terraform output -raw ingestor_function_name) \
  --payload '{"test": "event"}' \
  response.json
```

## 🔧 Common Commands

### View All Available Commands

```bash
make help
```

### Format Code

```bash
make fmt
```

### Validate Configuration

```bash
make validate
```

### Clean Artifacts

```bash
make clean
```

### View Terraform Outputs

```bash
terraform output                              # All outputs
terraform output ingestor_function_name       # Specific output
terraform output -raw processing_queue_url    # Raw value (no quotes)
```

## 📝 Making Changes

### Updating Lambda Code

1. Edit files in `lambdas/<function>/`
2. Run `terraform plan` - it will detect changes via hash
3. Run `terraform apply`

### Adding Environment Variables

1. Edit `terraform/variables.tf` to add new variable
2. Edit `terraform/main.tf` to use it in Lambda environment
3. Update `terraform/environments/*.tfvars` with values
4. Plan and apply

### Modifying Infrastructure

1. Edit relevant module or main.tf
2. Run `make plan ENV=dev` to preview
3. Run `make apply ENV=dev` to deploy

## 🐛 Troubleshooting

### Backend Already Exists

```bash
terraform init -backend-config=environments/dev-backend.tfvars -reconfigure
```

### State Lock Error

```bash
# Force unlock (use with caution)
terraform force-unlock <lock-id>
```

### Lambda Not Updating

```bash
# Taint and reapply
terraform taint module.lambda_analyzer.aws_lambda_function.this
terraform apply -var-file=environments/dev.tfvars
```

### Debug Mode

```bash
export TF_LOG=DEBUG
terraform plan -var-file=environments/dev.tfvars
```

## 📊 Monitoring & Operations

### Check System Health

```bash
# Queue depths
make check-queue

# Dead letter queues
make check-dlq

# CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=$(terraform output -raw analyzer_function_name) \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

### View Secrets

```bash
# List parameters
aws ssm describe-parameters

# Get parameter (with decryption)
aws ssm get-parameter \
  --name /mcp-first-responder/dev/anthropic-api-key \
  --with-decryption
```

## 🗑️ Destroying Infrastructure

### Development

```bash
make destroy ENV=dev
```

### Production (CAREFUL!)

```bash
make destroy ENV=prod
# Will require typing 'prod' to confirm
```

## 📚 Additional Resources

- [Main README](terraform/README.md) - Comprehensive documentation
- [CLAUDE.md](CLAUDE.md) - Project overview and architecture
- [Module READMEs](terraform/modules/) - Individual module documentation
- [Project Plan](MCP-First-Responder-Project-Plan.md) - Full implementation plan

## ⚡ Quick Reference

```bash
# Complete first-time setup
make setup-backend ENV=dev
export TF_VAR_anthropic_api_key="..."
export TF_VAR_slack_webhook_url="..."
export TF_VAR_owner_email="..."
make deploy ENV=dev

# Daily development
make plan ENV=dev      # Preview changes
make apply ENV=dev     # Apply changes
make logs-analyzer     # View logs

# Verify deployment
make output            # See all outputs
make test-ingestor     # Test Lambda
```

## 💡 Tips

1. **Always run `plan` before `apply`** to preview changes
2. **Use environment-specific tfvars** for different configs
3. **Never commit `terraform.tfvars`** (use example file)
4. **Test in dev first** before deploying to prod
5. **Monitor costs** via AWS Cost Explorer
6. **Enable CloudTrail** for audit logs in production
7. **Use the Makefile** for common operations - it's faster!

## 🆘 Need Help?

1. Run `make help` to see all available commands
2. Check `terraform/README.md` for detailed docs
3. Review module READMEs in `terraform/modules/*/README.md`
4. Check AWS CloudWatch logs for Lambda errors
5. Verify SSM parameters are set correctly
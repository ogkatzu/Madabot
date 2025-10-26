# MCP First-Responder Terraform Infrastructure

This directory contains the Terraform infrastructure as code (IaC) for the MCP First-Responder intelligent incident response system.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Module Structure](#module-structure)
- [Deployment Guide](#deployment-guide)
- [Configuration](#configuration)
- [Cost Estimation](#cost-estimation)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Overview

The MCP First-Responder infrastructure is built using modular Terraform components that deploy a serverless, event-driven incident response system on AWS. The system automatically:

1. Receives alerts from CloudWatch via EventBridge
2. Analyzes them using Claude AI (Anthropic)
3. Distributes intelligent reports to Slack, Jira, and email

## Architecture

```
CloudWatch Logs → EventBridge → Ingestor Lambda → SQS FIFO
                                                      ↓
                                              Analyzer Lambda ← Claude AI
                                                      ↓
                                                  DynamoDB
                                                      ↓
                                              Distribution Queue
                                                      ↓
                                              Notifier Lambda → Slack/Jira/Email
```

### Key Components

- **EventBridge**: Routes CloudWatch events to the ingestor
- **3 Lambda Functions**: Ingestor, Analyzer (Claude-powered), Slack Notifier
- **2 SQS FIFO Queues**: Processing and Distribution (with DLQs)
- **2 DynamoDB Tables**: Alerts storage and Analysis cache (with TTL)
- **SSM Parameter Store**: Secure secrets management
- **CloudWatch**: Logging and alarms

## Prerequisites

### Tools Required

- [Terraform](https://www.terraform.io/downloads) >= 1.5.0
- [AWS CLI](https://aws.amazon.com/cli/) >= 2.0
- AWS account with appropriate permissions
- [Python](https://www.python.org/) 3.11+ (for Lambda development)

### Secrets Required

- **Anthropic API Key**: Get from [Anthropic Console](https://console.anthropic.com/)
- **Slack Webhook URL**: Create a Slack app and get webhook
- **Jira API Token** (optional): For Jira integration

## Quick Start

### 1. Create S3 Backend (One-Time Setup)

```bash
# Create S3 bucket for Terraform state
aws s3 mb s3://mcp-first-responder-terraform-state-dev --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket mcp-first-responder-terraform-state-dev \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name mcp-first-responder-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### 2. Initialize Terraform

```bash
cd terraform
terraform init -backend-config=environments/dev-backend.tfvars
```

### 3. Configure Variables

```bash
export TF_VAR_anthropic_api_key="sk-ant-api03-..."
export TF_VAR_slack_webhook_url="https://hooks.slack.com/services/..."
export TF_VAR_owner_email="your-email@example.com"
```

### 4. Plan and Apply

```bash
# Review changes
terraform plan -var-file=environments/dev.tfvars

# Apply infrastructure
terraform apply -var-file=environments/dev.tfvars
```

## Module Structure

```
terraform/
├── main.tf                 # Root module - orchestrates all resources
├── variables.tf            # Input variables with validation
├── outputs.tf              # Exported values and helper commands
├── providers.tf            # AWS provider configuration
├── versions.tf             # Terraform and provider version constraints
├── backend.tf              # S3 backend configuration
├── terraform.tfvars.example # Example configuration file
├── environments/           # Environment-specific configurations
│   ├── dev.tfvars
│   ├── staging.tfvars
│   ├── prod.tfvars
│   └── *-backend.tfvars
└── modules/                # Reusable Terraform modules
    ├── iam/                # IAM roles and policies
    ├── dynamodb/           # DynamoDB tables with GSI/TTL
    ├── sqs/                # SQS queues with DLQ
    ├── lambda/             # Lambda functions with packaging
    └── eventbridge/        # EventBridge rules and targets
```

## Deployment Guide

### Development Environment

```bash
terraform init -backend-config=environments/dev-backend.tfvars
terraform plan -var-file=environments/dev.tfvars
terraform apply -var-file=environments/dev.tfvars
```

### Production Environment

```bash
terraform init -backend-config=environments/prod-backend.tfvars -reconfigure
terraform plan -var-file=environments/prod.tfvars
terraform apply -var-file=environments/prod.tfvars
```

## Configuration

### Key Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `environment` | Environment name (dev/staging/prod) | - | Yes |
| `aws_region` | AWS region | us-east-1 | No |
| `anthropic_api_key` | Claude API key | - | Yes |
| `slack_webhook_url` | Slack webhook URL | - | Yes |
| `analyzer_memory_size` | Memory for analyzer Lambda (MB) | 1024 | No |
| `cache_ttl_hours` | Cache TTL in hours | 24 | No |

## Cost Estimation

Monthly costs for 100 alerts/day (3,000/month):

| Service | Cost |
|---------|------|
| Lambda | $8 |
| DynamoDB | $2 |
| SQS | $0.01 |
| CloudWatch | $2.50 |
| **Claude API** | **~$45** |
| **Total** | **~$58/month** |

## Monitoring

### View Logs

```bash
# View outputs
terraform output

# Tail logs
aws logs tail $(terraform output -raw ingestor_log_group) --follow
```

### Check Queues

```bash
# Queue depth
aws sqs get-queue-attributes \
  --queue-url $(terraform output -raw processing_queue_url) \
  --attribute-names ApproximateNumberOfMessagesVisible

# Check DLQ
aws sqs receive-message \
  --queue-url $(terraform output -raw processing_dlq_url)
```

## Troubleshooting

### Common Issues

**Terraform Init Fails**:
```bash
terraform init -backend-config=environments/dev-backend.tfvars -reconfigure
```

**Lambda Not Updating**:
```bash
terraform taint module.lambda_analyzer.aws_lambda_function.this
terraform apply -var-file=environments/dev.tfvars
```

**Debug Mode**:
```bash
export TF_LOG=DEBUG
terraform plan -var-file=environments/dev.tfvars
```

## Best Practices

1. Never commit secrets to version control
2. Always run `terraform plan` before `apply`
3. Use separate backends per environment
4. Tag all resources for cost tracking
5. Test in dev before deploying to prod

## Support

For issues or questions:
1. Check [CLAUDE.md](../CLAUDE.md)
2. Review AWS CloudWatch logs
3. Check [project plan](../MCP-First-Responder-Project-Plan.md)
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MCP First-Responder: Intelligent Incident Response System** - An AI-powered serverless incident response system that automatically receives CloudWatch alerts, analyzes them using Claude AI, and delivers intelligent incident reports to Slack, Jira, and email.

**Status**: Hackathon project (3-4 days timeline)
**Architecture**: Event-driven serverless (AWS Lambda + EventBridge + SQS + DynamoDB)
**Language**: Python 3.11+
**Infrastructure**: Terraform (planned) or AWS SAM

## Project Structure

The project follows a **three-stage pipeline architecture**:

```
Alert Sources → EventBridge → Ingestor Lambda → SQS FIFO → Analyzer Lambda → Distribution Queue → Notifier Lambdas
                                                              ↓
                                                          DynamoDB
```

### Key Directories

- `lambdas/` - Lambda function code organized by component
  - `ingestor/` - Normalizes and enriches incoming alerts
  - `analyzer/` - AI-powered analysis engine (core component)
  - `slack_notifier/` - Slack Block Kit formatted notifications
  - `jira_notifier/` - Jira ticket creation
  - `email_notifier/` - SES email notifications
- `terraform/` - Infrastructure as Code definitions
- `scripts/` - Deployment and testing utilities
- `docs/` - Architecture and operational documentation
- `archive/` - Reference implementation (AWS SAM-based prototype)

## Development Commands

### Infrastructure Deployment

```bash
# Initialize Terraform
cd terraform
terraform init

# Plan infrastructure changes
terraform plan -var-file=environments/dev.tfvars

# Apply infrastructure
terraform apply -var-file=environments/dev.tfvars

# Destroy infrastructure
terraform destroy -var-file=environments/dev.tfvars
```

### Lambda Development

```bash
# Install dependencies for a Lambda
cd lambdas/<function-name>
pip install -r requirements.txt

# Run unit tests
python -m pytest tests/

# Package Lambda for deployment (if needed)
zip -r function.zip . -x "tests/*" "*.pyc"
```

### Testing

```bash
# Generate test alerts
python scripts/demo_data_generator.py

# End-to-end testing
python scripts/test_e2e.py

# Test individual Lambda locally (requires AWS SAM)
sam local invoke AnalysisFunction -e tests/events/test-alert.json
```

### Monitoring & Debugging

```bash
# View Lambda logs
aws logs tail /aws/lambda/<function-name> --follow

# Check SQS queue depth
aws sqs get-queue-attributes \
  --queue-url <queue-url> \
  --attribute-names ApproximateNumberOfMessagesVisible

# Query recent alerts from DynamoDB
aws dynamodb scan --table-name <env>-alerts --limit 10

# Check Dead Letter Queue
aws sqs receive-message --queue-url <dlq-url> --max-number-of-messages 10
```

## Architecture Details

### 1. Alert Ingestor (`lambdas/ingestor/handler.py`)

**Responsibility**: Normalize alerts from multiple sources into standardized format

**Key Functions**:
- Receives CloudWatch events via EventBridge
- Enriches with AWS metadata (service tags, region, account)
- Sends normalized alert to SQS FIFO queue
- Implements deduplication logic

**Input Sources**:
- CloudWatch Alarms
- CloudWatch Logs (via subscription filters)
- SNS notifications
- Custom webhooks

**Output Format**:
```json
{
  "alert_id": "unique-hash",
  "source": "cloudwatch_logs|cloudwatch_alarm|sns",
  "source_id": "original-id",
  "title": "Human-readable title",
  "message": "Detailed message with stack traces",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "timestamp": "ISO-8601",
  "service_tags": {...},
  "raw_data": {...}
}
```

### 2. Analyzer (Core Component - `lambdas/analyzer/handler.py`)

**Responsibility**: AI-powered analysis using Claude Sonnet 3.5/4

**Processing Pipeline**:
1. **Context Gathering** (`context.py`):
   - Fetches last 50 CloudWatch log entries
   - Retrieves infrastructure state (EC2, ECS, ALB health)
   - Checks recent deployments/CloudFormation changes
   - Queries historical patterns from DynamoDB
   - Fetches relevant code snippets from S3 (if available)

2. **Claude Analysis** (`claude_client.py`):
   - Sends comprehensive context to Claude API
   - Requests structured JSON response
   - Parses: root cause, impact, severity, remediation steps

3. **Response Caching**:
   - Cache key: `hash(source + title + error_type)`
   - TTL: 24 hours (DynamoDB TTL)
   - 60-80% cache hit rate reduces API costs

**Key Environment Variables**:
- `ANTHROPIC_API_KEY` - Claude API key
- `ALERTS_TABLE` - DynamoDB table for alerts
- `ANALYSIS_CACHE_TABLE` - DynamoDB cache table
- `DISTRIBUTION_QUEUE_URL` - SQS queue for distribution

**Expected Analysis Output**:
```json
{
  "root_cause": "Hypothesis about the underlying cause",
  "severity_assessment": "Validation or adjustment of severity",
  "impact": "Systems/users affected",
  "remediation_steps": ["step1", "step2", "step3"],
  "monitoring_recommendations": ["metric1", "metric2"],
  "confidence_score": 0.85
}
```

### 3. Distribution Layer (`lambdas/slack_notifier/`, `jira_notifier/`, `email_notifier/`)

**Slack Notifier** (`slack_notifier/handler.py`):
- Uses Slack Block Kit for rich formatting
- Color coding by severity (red=CRITICAL, orange=HIGH, yellow=MEDIUM, blue=LOW)
- Interactive buttons: "Acknowledge", "Create Jira", "View Logs"
- Threaded conversations for updates
- Deep links to CloudWatch Insights

**Jira Notifier** (`jira_notifier/handler.py`):
- Creates incident tickets with full context
- Maps severity to Jira priority
- Links to Slack thread and CloudWatch
- Custom fields for service, analysis results

**Email Notifier** (`email_notifier/handler.py`):
- HTML email template with styling
- Recipient routing based on service/severity
- Includes analysis and action items

## Infrastructure (Terraform)

### Key Resources

- **EventBridge Rule**: Filters CloudWatch events (ERROR, WARN, CRITICAL patterns)
- **SQS FIFO Queues**:
  - Processing Queue (reception → analysis): 15min visibility timeout, 3 retries
  - Distribution Queue (analysis → notifiers): 5min visibility timeout
  - Dead Letter Queues for both
- **DynamoDB Tables**:
  - `AlertsTable`: Stores alerts + analysis (GSI on severity+timestamp)
  - `AnalysisCacheTable`: Cache with TTL enabled
- **Lambda Functions**:
  - Ingestor: 512MB, 5min timeout
  - Analyzer: 1024MB, 15min timeout (for Claude API latency)
  - Notifiers: 512MB, 5min timeout
- **IAM Roles**: Least-privilege policies for each Lambda

## Development Workflow

### Adding New Alert Source

1. Edit `lambdas/ingestor/handler.py`
2. Add detection logic in normalization function
3. Create parser for source-specific format
4. Add sample event to `tests/events/`
5. Update EventBridge rule pattern in `terraform/eventbridge.tf`

### Modifying Claude Analysis

1. Edit system prompt in `lambdas/analyzer/handler.py`
2. Update context gathering in `lambdas/analyzer/context.py`
3. Adjust expected JSON output structure
4. Update cache key generation if needed
5. Test with real alerts to validate improvements

### Adding Distribution Channel

1. Create new directory: `lambdas/<channel>_notifier/`
2. Implement handler with message formatting
3. Add environment variables in `terraform/lambda.tf`
4. Create Terraform resource for Lambda
5. Add SQS trigger from Distribution Queue
6. Update IAM policies for external service access

## Critical Implementation Details

### Error Handling Strategy

- **SQS Retry Logic**: 3 attempts with exponential backoff, then DLQ
- **Circuit Breaker**: For external APIs (Slack, Jira, Anthropic)
- **Graceful Degradation**: If Jira fails, still send Slack notification
- **DLQ Monitoring**: CloudWatch alarm when DLQ depth > 0

### Cost Optimization

**Expected Costs** (100 alerts/day):
- Lambda: ~$8/month
- DynamoDB: ~$2/month
- SQS: ~$0.004/month
- **Claude API: ~$45/month (80% of costs)**
- Total: ~$58/month

**Optimization Strategies**:
- Analysis caching (24h TTL) reduces API calls by 60-80%
- Use Claude Haiku for simple classification tasks
- Batch low-priority alerts
- Implement rate limiting for noisy sources

### Demo Preparation

**Demo Flow** (5-7 minutes):
1. Trigger simulated database error
2. Show CloudWatch log entry
3. Wait for Slack notification (<1 minute)
4. Highlight intelligent analysis
5. Click "Create Jira" button
6. Show auto-created Jira ticket
7. Trigger second scenario (memory leak)
8. Show infrastructure context gathering
9. Present value proposition and cost analysis

**Demo Data Generator** (`scripts/demo_data_generator.py`):
- Realistic error scenarios: DB failures, API timeouts, memory leaks, deployment rollbacks
- Timing control for live presentation
- Different severity levels

## Important Notes

- **Terraform State**: Store in S3 with DynamoDB locking (configure backend)
- **Secrets Management**: Use AWS Systems Manager Parameter Store (NoEcho parameters)
- **API Authentication**: EventBridge to Lambda uses IAM; external webhooks use API Gateway with API keys
- **FIFO Queues**: Ensure message group ID is set for ordering guarantees
- **Claude API**: Rate limits apply; implement exponential backoff
- **Caching**: Critical for cost control; verify TTL is enabled on DynamoDB table

## Reference Implementation

The `archive/` directory contains a working AWS SAM-based prototype with:
- Complete Lambda handlers (reception, analysis, distribution)
- SAM template (CloudFormation-based)
- Deployment scripts
- Comprehensive documentation

Use this as reference when building the Terraform-based production version. Key differences:
- Archive uses AWS SAM/CloudFormation; production uses Terraform
- Archive uses API Gateway webhook; production uses EventBridge
- Same core logic for analysis and distribution can be reused

## Troubleshooting

**Alerts Not Processing**:
1. Check EventBridge rule metrics
2. Verify Lambda execution role permissions
3. Check SQS queue configuration (FIFO settings, visibility timeout)
4. Review Lambda CloudWatch logs

**High Claude API Costs**:
1. Verify cache hit rate in logs
2. Check TTL is enabled on cache table
3. Review error signature generation
4. Consider implementing alert throttling

**Distribution Failures**:
1. Verify Slack webhook URL validity (test with curl)
2. Check Jira credentials and project permissions
3. Confirm Lambda has internet access (NAT Gateway if in VPC)
4. Review CloudWatch logs for HTTP response codes

## Phase-Based Development Plan

**Phase 1 (Day 1)**: MVP - CloudWatch Error → Claude Analysis → Slack
**Phase 2 (Day 2)**: Enhanced context gathering + rich Slack formatting
**Phase 3 (Day 3)**: Jira/Email integration + production hardening
**Phase 4 (Day 4)**: Demo preparation + final polish

Refer to `MCP-First-Responder-Project-Plan.md` for detailed task breakdown and timeline.

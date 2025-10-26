# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP Intelligent Incident Response System - An AI-powered serverless incident response system that receives alerts from CloudWatch and other sources, performs intelligent analysis using Claude AI, and distributes actionable reports to Slack, Jira, and Email.

**Architecture**: Event-driven serverless (AWS Lambda + SQS + DynamoDB)
**Language**: Python 3.12
**Infrastructure**: AWS SAM (CloudFormation)

## Key Commands

### Deployment

```bash
# Deploy the system
./deploy.sh \
  --bucket <s3-deployment-bucket> \
  --environment <dev|staging|prod> \
  --slack-webhook "<webhook-url>" \
  --anthropic-key "<api-key>"

# Build SAM application locally
sam build

# Package for deployment
sam package --template-file template.yaml --s3-bucket <bucket> --output-template-file packaged.yaml

# Deploy stack
sam deploy --template-file packaged.yaml --stack-name <name> --capabilities CAPABILITY_IAM
```

### Testing

```bash
# Test webhook endpoint
curl -X POST <webhook-url> \
  -H "Content-Type: application/json" \
  -H "x-api-key: <api-key>" \
  -d @tests/events/sample-alert.json

# Local Lambda testing
sam local invoke AnalysisFunction -e tests/events/alert.json

# Install dependencies locally
pip install -r requirements.txt
```

### Monitoring & Debugging

```bash
# View Lambda logs
sam logs -n <FunctionName> --stack-name <stack-name> --tail

# Check DLQ for failed messages
aws sqs receive-message --queue-url <dlq-url> --max-number-of-messages 10

# Query recent alerts from DynamoDB
aws dynamodb scan --table-name <env>-alerts --limit 10

# Monitor processing queue depth
aws sqs get-queue-attributes --queue-url <queue-url> --attribute-names ApproximateNumberOfMessagesVisible

# View CloudWatch Logs Insights
aws logs start-query --log-group-name /aws/lambda/<function> --query-string '<query>' ...
```

## Architecture Overview

The system follows a **three-stage pipeline architecture**:

### 1. Reception Layer (`src/reception/handler.py`)
- **Entry point**: API Gateway webhook (`/alert` endpoint)
- **Responsibility**: Normalizes alerts from multiple sources into common format
- **Sources supported**: CloudWatch Alarms, CloudWatch Logs, SNS, generic webhooks
- **Output**: Sends normalized alert to Processing Queue (SQS)

**Key functions**:
- `receive_alert()` - Main Lambda handler
- `normalize_alert()` - Routes to appropriate normalization function
- `normalize_cloudwatch_alarm()`, `normalize_sns_alert()`, etc. - Source-specific handlers

### 2. Analysis Engine (`src/analysis/handler.py`)
- **Trigger**: SQS Processing Queue messages
- **Responsibility**: AI-powered analysis using Claude Sonnet 4
- **Key features**:
  - Context gathering from CloudWatch Logs and DynamoDB
  - Analysis caching (1-hour TTL) to reduce API costs
  - Historical pattern recognition
  - Structured JSON output with root cause, impact, remediation steps
- **Output**: Sends alert + analysis to Distribution Queue

**Key functions**:
- `analyze_alert()` - Main handler
- `gather_context()` - Collects historical patterns and log context
- `check_analysis_cache()` - Cache lookup using error signature
- `perform_claude_analysis()` - Claude API interaction
- `cache_analysis()` - Store analysis for reuse

**Cache strategy**: Error signature = hash(source + title + error_type), TTL 24h

### 3. Distribution Layer (`src/distribution/handler.py`)
- **Trigger**: SQS Distribution Queue messages
- **Responsibility**: Multi-channel notification delivery
- **Channels**: Slack (required), Jira (optional), Email (optional)
- **Output**: Formatted notifications to external systems

**Key functions**:
- `distribute_report()` - Main handler
- `send_to_slack()` - Slack Block Kit formatted messages
- `format_slack_message()` - Rich formatting with severity colors and emojis
- `send_to_jira()`, `send_to_email()` - Optional integrations

## Infrastructure (template.yaml)

**Key resources**:
- `AlertWebhookApi` - API Gateway with API key authentication
- `AlertReceptionFunction` - Reception Lambda (512MB, 5min timeout)
- `AnalysisFunction` - Analysis Lambda (1024MB, 15min timeout)
- `DistributionFunction` - Distribution Lambda (512MB, 5min timeout)
- `ProcessingQueue` - SQS between reception and analysis (15min visibility timeout, 3 retries → DLQ)
- `DistributionQueue` - SQS between analysis and distribution
- `AlertsTable` - DynamoDB with GSI on severity+timestamp
- `AnalysisCacheTable` - DynamoDB with TTL enabled

**Important**: All Lambdas share environment variables for table names via `Globals.Function.Environment`

## Data Flow

```
CloudWatch → API Gateway → Reception Lambda → Processing Queue (SQS)
                                                       ↓
                                                 Analysis Lambda
                                                       ↓
                              DynamoDB ← stores alert + analysis + cache
                                                       ↓
                                              Distribution Queue (SQS)
                                                       ↓
                                              Distribution Lambda
                                                       ↓
                                          Slack / Jira / Email
```

**Error handling**: Each SQS queue has 3 retry attempts, then messages go to Dead Letter Queue (DLQ)

## Alert Normalization

All alerts are converted to this standard format:

```json
{
  "alert_id": "unique-hash",
  "source": "cloudwatch_logs|cloudwatch_alarm|sns|generic",
  "source_id": "original-id",
  "title": "Human-readable title",
  "message": "Detailed message",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "timestamp": "ISO-8601",
  "raw_data": {...}
}
```

**Detection logic in `normalize_alert()`**:
- If `Records` + `EventSource=aws:sns` → SNS alert
- If `AlarmName` present → CloudWatch Alarm
- If `logEvents` present → CloudWatch Logs
- Otherwise → Generic webhook

## AI Analysis Prompt Structure

The system uses structured prompts in `src/analysis/handler.py`:

**System prompt**: Defines Claude's role as expert DevOps analyst
**User prompt**: Includes alert details + historical context + log context

**Expected output** (JSON):
```json
{
  "root_cause": "hypothesis about cause",
  "severity_assessment": "validation or adjustment",
  "impact": "what is affected",
  "remediation_steps": ["step1", "step2"],
  "monitoring_recommendations": ["metric1", "metric2"]
}
```

## Cost Optimization Strategy

1. **Analysis caching**: 60-80% cache hit rate saves ~$18/month on Claude API calls
2. **Error signature**: `hash(source + title + error_type)` for cache key
3. **TTL**: Cache entries expire after 24 hours (DynamoDB TTL)
4. **Lambda memory**: Right-sized for workload (Reception: 512MB, Analysis: 1024MB)

**Expected costs at 1000 alerts/month**: ~$40 total

## Environment Variables

**Global** (all Lambdas):
- `ENVIRONMENT` - dev/staging/prod
- `ALERTS_TABLE` - DynamoDB table name for alerts
- `ANALYSIS_CACHE_TABLE` - DynamoDB table name for cache

**Reception**:
- `PROCESSING_QUEUE_URL` - SQS queue for analysis

**Analysis**:
- `ANTHROPIC_API_KEY` - Claude API key (NoEcho parameter)
- `DISTRIBUTION_QUEUE_URL` - SQS queue for distribution

**Distribution**:
- `SLACK_WEBHOOK_URL` - Required for Slack notifications
- `JIRA_ENABLED` - Optional (true/false)
- `JIRA_URL`, `JIRA_API_TOKEN`, `JIRA_PROJECT` - Optional Jira config
- `EMAIL_ENABLED` - Optional (true/false)
- `EMAIL_FROM`, `EMAIL_TO` - Optional email config

## Common Development Tasks

### Adding a New Alert Source

1. Edit `src/reception/handler.py`
2. Add detection logic in `normalize_alert()`
3. Create new `normalize_<source>_alert()` function
4. Test with sample payload in `tests/events/`

### Customizing Claude Analysis

1. Edit `src/analysis/handler.py`
2. Modify `get_system_prompt()` for behavior changes
3. Update user prompt format in `perform_claude_analysis()`
4. Adjust expected output JSON structure

### Adding a Distribution Channel

1. Edit `src/distribution/handler.py`
2. Add environment variables in `template.yaml`
3. Create `send_to_<channel>()` function
4. Call from `distribute_report()` main handler
5. Update IAM policies if AWS service integration needed

## Troubleshooting Guide

**Alerts not processing**:
- Check API Gateway logs: `aws apigateway get-stage --rest-api-id <id> --stage-name <env>`
- Verify API key: Output from deployment or check AWS Console
- Check Lambda errors: `sam logs -n AlertReceptionFunction --tail`
- Inspect SQS queue: `aws sqs get-queue-attributes --queue-url <url>`

**High Claude API costs**:
- Check cache hit rate in CloudWatch Logs
- Verify TTL is set on `AnalysisCacheTable`
- Review error signature generation logic
- Consider implementing alert throttling for noisy sources

**DLQ has messages**:
- Retrieve messages: `aws sqs receive-message --queue-url <dlq-url>`
- Common causes: Claude API errors, invalid JSON, missing env vars
- Fix root cause and manually reprocess or purge

**Slack notifications failing**:
- Verify webhook URL is valid (test with curl)
- Check Lambda has internet access (NAT Gateway if in VPC)
- Review message format against Slack Block Kit spec
- Check CloudWatch logs for HTTP response codes

## Dependencies

**Python packages** (`requirements.txt`):
- `anthropic==0.39.0` - Claude API client
- `boto3==1.35.0` - AWS SDK
- `urllib3==2.2.0` - HTTP client for webhooks

**AWS services**:
- Lambda (Python 3.12 runtime)
- API Gateway (REST API with API key auth)
- SQS (Standard queues)
- DynamoDB (on-demand billing)
- CloudWatch Logs & Alarms

## Documentation

- `README.md` - Feature overview and quick start
- `START_HERE.md` - Quick deployment guide
- `IMPLEMENTATION_GUIDE.md` - Detailed setup instructions
- `docs/ARCHITECTURE.md` - Deep dive on design decisions
- `docs/OPERATIONS.md` - Operations runbook with scripts
- `tests/SAMPLE_ALERTS.md` - Testing guide with examples

## Important Notes

- **No git repo**: Project is not currently under version control
- **Credentials**: Never commit `.env`, API keys, or webhook URLs
- **Dependencies**: Install to function directories for SAM: `pip install -r requirements.txt -t src/<function>/`
- **API Gateway**: Uses API key auth (not IAM or JWT)
- **Caching**: Critical for cost control - verify cache table TTL is enabled
- **Retries**: SQS retry logic = 3 attempts, then DLQ (prevents infinite loops)
- **Timeouts**: Reception (5min), Analysis (15min), Distribution (5min) - designed for Claude API latency

## Quick Reference: Key Files

- `template.yaml` - SAM infrastructure definition (221 lines)
- `deploy.sh` - Automated deployment script
- `src/reception/handler.py` - Alert ingestion (~350 lines)
- `src/analysis/handler.py` - AI analysis engine (~450 lines)
- `src/distribution/handler.py` - Multi-channel delivery (~400 lines)
- `requirements.txt` - Python dependencies
- `cloudwatch-integration.yaml` - Optional CloudWatch setup automation

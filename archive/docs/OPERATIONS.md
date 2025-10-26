# Operations Runbook - MCP Incident Response System

## Table of Contents
1. [Daily Operations](#daily-operations)
2. [Health Checks](#health-checks)
3. [Common Operational Tasks](#common-operational-tasks)
4. [Incident Response](#incident-response)
5. [Maintenance Procedures](#maintenance-procedures)
6. [Performance Tuning](#performance-tuning)
7. [Cost Management](#cost-management)

## Daily Operations

### Morning Checks (5 minutes)

```bash
#!/bin/bash
# daily-health-check.sh

STACK_NAME="mcp-incident-responder-prod"
REGION="us-east-1"

echo "=== Daily Health Check - $(date) ==="

# 1. Check DLQ for failed messages
DLQ_MESSAGES=$(aws sqs get-queue-attributes \
  --queue-url $(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`DeadLetterQueueUrl`].OutputValue' \
    --output text) \
  --attribute-names ApproximateNumberOfMessages \
  --query 'Attributes.ApproximateNumberOfMessages' \
  --output text)

echo "DLQ Messages: $DLQ_MESSAGES"
if [ "$DLQ_MESSAGES" -gt 0 ]; then
  echo "⚠️  WARNING: Messages in DLQ require investigation"
fi

# 2. Check Lambda error rates (last 24 hours)
for FUNCTION in AlertReceptionFunction AnalysisFunction DistributionFunction; do
  ERRORS=$(aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Errors \
    --dimensions Name=FunctionName,Value=$STACK_NAME-$FUNCTION \
    --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 86400 \
    --statistics Sum \
    --query 'Datapoints[0].Sum' \
    --output text)
  
  echo "$FUNCTION Errors (24h): ${ERRORS:-0}"
done

# 3. Check processing throughput
ALERTS_PROCESSED=$(aws dynamodb scan \
  --table-name $STACK_NAME-alerts \
  --filter-expression "created_at >= :yesterday" \
  --expression-attribute-values '{":yesterday":{"S":"'$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S)'"}}' \
  --select COUNT \
  --query 'Count' \
  --output text)

echo "Alerts Processed (24h): $ALERTS_PROCESSED"

# 4. Check cache hit rate
echo "Cache metrics available in CloudWatch Insights - run manual query"

echo "=== Health Check Complete ==="
```

### Weekly Review (30 minutes)

1. **Cost Analysis**
   ```bash
   aws ce get-cost-and-usage \
     --time-period Start=$(date -d '7 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
     --granularity DAILY \
     --metrics BlendedCost \
     --group-by Type=SERVICE
   ```

2. **Performance Review**
   - Review average Lambda durations
   - Check for increasing trends
   - Identify optimization opportunities

3. **Alert Analysis**
   - Most common alert types
   - Severity distribution
   - False positive rate

## Health Checks

### System Health Dashboard

Create a CloudWatch Dashboard with these widgets:

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Invocations", {"stat": "Sum"}],
          [".", "Errors"],
          [".", "Throttles"]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "Lambda Health"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/SQS", "ApproximateNumberOfMessagesVisible"],
          [".", "ApproximateAgeOfOldestMessage"]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Queue Health"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/DynamoDB", "ConsumedReadCapacityUnits"],
          [".", "ConsumedWriteCapacityUnits"]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "DynamoDB Usage"
      }
    }
  ]
}
```

### Automated Health Check Script

```bash
#!/bin/bash
# health-check.sh - Run this every 5 minutes via cron or CloudWatch Events

check_component() {
  local component=$1
  local metric=$2
  local threshold=$3
  
  value=$(aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name $metric \
    --dimensions Name=FunctionName,Value=$component \
    --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Sum \
    --query 'Datapoints[0].Sum' \
    --output text)
  
  if [ "$value" -gt "$threshold" ]; then
    send_alert "$component $metric exceeded threshold: $value > $threshold"
  fi
}

send_alert() {
  local message=$1
  # Send to SNS or Slack
  aws sns publish \
    --topic-arn $ALERT_TOPIC_ARN \
    --message "$message"
}

# Check all components
check_component "AlertReceptionFunction" "Errors" 10
check_component "AnalysisFunction" "Errors" 5
check_component "DistributionFunction" "Errors" 5
```

## Common Operational Tasks

### 1. Update Slack Webhook URL

```bash
aws secretsmanager update-secret \
  --secret-id mcp-responder/slack-webhook \
  --secret-string "https://hooks.slack.com/services/NEW/WEBHOOK/URL"

# Restart Lambdas to pick up new value
aws lambda update-function-configuration \
  --function-name mcp-incident-responder-prod-DistributionFunction \
  --environment Variables={SLACK_WEBHOOK_URL=placeholder}
```

### 2. Update Anthropic API Key

```bash
aws secretsmanager update-secret \
  --secret-id mcp-responder/anthropic-key \
  --secret-string "sk-ant-api03-NEW-KEY"
```

### 3. Clear Analysis Cache

```bash
# Clear all cached analyses
aws dynamodb scan \
  --table-name mcp-incident-responder-prod-analysis-cache \
  --projection-expression "error_signature" \
  --output json | \
jq -r '.Items[].error_signature.S' | \
while read signature; do
  aws dynamodb delete-item \
    --table-name mcp-incident-responder-prod-analysis-cache \
    --key "{\"error_signature\":{\"S\":\"$signature\"}}"
done
```

### 4. Reprocess Failed Messages from DLQ

```bash
#!/bin/bash
# reprocess-dlq.sh

DLQ_URL="your-dlq-url"
TARGET_QUEUE_URL="your-processing-queue-url"

while true; do
  # Receive message from DLQ
  MESSAGE=$(aws sqs receive-message \
    --queue-url $DLQ_URL \
    --max-number-of-messages 1 \
    --output json)
  
  if [ $(echo $MESSAGE | jq '.Messages | length') -eq 0 ]; then
    echo "No more messages in DLQ"
    break
  fi
  
  # Extract message body and receipt handle
  BODY=$(echo $MESSAGE | jq -r '.Messages[0].Body')
  RECEIPT=$(echo $MESSAGE | jq -r '.Messages[0].ReceiptHandle')
  
  # Send to target queue
  aws sqs send-message \
    --queue-url $TARGET_QUEUE_URL \
    --message-body "$BODY"
  
  # Delete from DLQ
  aws sqs delete-message \
    --queue-url $DLQ_URL \
    --receipt-handle "$RECEIPT"
  
  echo "Reprocessed 1 message"
  sleep 1
done
```

### 5. Query Alert History

```bash
# Get all critical alerts from last 24 hours
aws dynamodb query \
  --table-name mcp-incident-responder-prod-alerts \
  --index-name timestamp-index \
  --key-condition-expression "severity = :sev AND #ts > :time" \
  --expression-attribute-names '{"#ts":"timestamp"}' \
  --expression-attribute-values '{
    ":sev":{"S":"CRITICAL"},
    ":time":{"N":"'$(date -d '24 hours ago' +%s)'"}
  }'

# Get specific alert by ID
aws dynamodb get-item \
  --table-name mcp-incident-responder-prod-alerts \
  --key '{"alert_id":{"S":"abc123"}}'
```

### 6. Manual Alert Injection (Testing)

```bash
# Send test alert
WEBHOOK_URL=$(aws cloudformation describe-stacks \
  --stack-name mcp-incident-responder-prod \
  --query 'Stacks[0].Outputs[?OutputKey==`WebhookUrl`].OutputValue' \
  --output text)

API_KEY=$(aws apigateway get-api-keys \
  --include-values \
  --query 'items[0].value' \
  --output text)

curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
    "source": "manual-test",
    "title": "Manual Test Alert",
    "message": "Testing the incident response system",
    "severity": "LOW",
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
  }'
```

## Incident Response

### System Down - No Alerts Processing

**Symptoms**: No alerts being received, Slack channels quiet

**Investigation Steps**:
1. Check API Gateway metrics
2. Check Lambda invocation count
3. Check SQS queue depth
4. Check CloudWatch Logs

**Resolution**:
```bash
# 1. Check if Lambdas are throttled
aws lambda get-function-concurrency \
  --function-name mcp-incident-responder-prod-AnalysisFunction

# 2. Check Lambda errors
aws logs tail /aws/lambda/mcp-incident-responder-prod-AnalysisFunction --follow

# 3. Check queue visibility
aws sqs get-queue-attributes \
  --queue-url $QUEUE_URL \
  --attribute-names All

# 4. If needed, purge queue and restart
aws sqs purge-queue --queue-url $QUEUE_URL
```

### High Anthropic API Costs

**Symptoms**: Unexpected high costs, bill alerts

**Investigation**:
```bash
# Check cache hit rate
aws logs insights query-logs \
  --log-group-name /aws/lambda/mcp-incident-responder-prod-AnalysisFunction \
  --start-time $(date -d '7 days ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /Using cached analysis/ | stats count()'

# Check alert volume
aws dynamodb scan \
  --table-name mcp-incident-responder-prod-alerts \
  --select COUNT
```

**Resolution**:
1. Review and optimize error signatures
2. Increase cache TTL
3. Implement alert throttling
4. Use Claude Haiku for low-priority alerts

### Slack Messages Not Delivered

**Symptoms**: Alerts processing but no Slack notifications

**Investigation**:
```bash
# Check distribution function logs
aws logs tail /aws/lambda/mcp-incident-responder-prod-DistributionFunction \
  --filter-pattern "ERROR" \
  --follow

# Test Slack webhook manually
SLACK_WEBHOOK=$(aws secretsmanager get-secret-value \
  --secret-id mcp-responder/slack-webhook \
  --query SecretString \
  --output text)

curl -X POST "$SLACK_WEBHOOK" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test message"}'
```

**Resolution**:
1. Verify Slack webhook URL is valid
2. Regenerate webhook if necessary
3. Check Lambda has internet access (NAT Gateway if in VPC)
4. Review Slack API rate limits

## Maintenance Procedures

### Deploying Updates

```bash
# 1. Test in dev environment first
./deploy.sh --environment dev --bucket dev-deployment-bucket

# 2. Run integration tests
./tests/integration-tests.sh dev

# 3. Deploy to staging
./deploy.sh --environment staging --bucket staging-deployment-bucket

# 4. Smoke test staging
./tests/smoke-tests.sh staging

# 5. Deploy to production with canary
sam deploy \
  --stack-name mcp-incident-responder-prod \
  --parameter-overrides DeploymentPreference=Canary10Percent10Minutes

# 6. Monitor canary deployment
watch -n 10 'aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=mcp-incident-responder-prod-AnalysisFunction \
  --start-time $(date -u -d "10 minutes ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 600 \
  --statistics Sum'

# 7. If errors detected, rollback
aws cloudformation cancel-update-stack \
  --stack-name mcp-incident-responder-prod
```

### Database Maintenance

```bash
# 1. Export alerts for backup
aws dynamodb export-table-to-point-in-time \
  --table-arn arn:aws:dynamodb:region:account:table/alerts \
  --s3-bucket backups \
  --s3-prefix dynamodb-exports/

# 2. Clean old alerts (if not using TTL)
aws dynamodb scan \
  --table-name mcp-incident-responder-prod-alerts \
  --filter-expression "created_at < :cutoff" \
  --expression-attribute-values '{":cutoff":{"S":"'$(date -d '90 days ago' +%Y-%m-%d)'"}}' \
  --projection-expression "alert_id" | \
jq -r '.Items[].alert_id.S' | \
while read id; do
  aws dynamodb delete-item \
    --table-name mcp-incident-responder-prod-alerts \
    --key "{\"alert_id\":{\"S\":\"$id\"}}"
done
```

### Log Management

```bash
# Set retention policy for all log groups
for LOG_GROUP in $(aws logs describe-log-groups \
  --log-group-name-prefix /aws/lambda/mcp-incident-responder \
  --query 'logGroups[].logGroupName' \
  --output text); do
  
  aws logs put-retention-policy \
    --log-group-name $LOG_GROUP \
    --retention-in-days 30
  
  echo "Set retention for $LOG_GROUP"
done
```

## Performance Tuning

### Lambda Memory Optimization

```bash
# Test different memory configurations
for MEMORY in 512 1024 1536 2048; do
  echo "Testing with ${MEMORY}MB..."
  
  aws lambda update-function-configuration \
    --function-name mcp-incident-responder-dev-AnalysisFunction \
    --memory-size $MEMORY
  
  sleep 30  # Wait for update
  
  # Send 100 test alerts
  for i in {1..100}; do
    # Send test alert
  done
  
  # Measure average duration
  aws logs insights query-logs \
    --log-group-name /aws/lambda/mcp-incident-responder-dev-AnalysisFunction \
    --start-time $(date -d '5 minutes ago' +%s) \
    --end-time $(date +%s) \
    --query-string 'stats avg(@duration)' \
    --query 'results[0][0].value'
done
```

### Analysis Cache Tuning

```python
# Analyze cache effectiveness
import boto3
from datetime import datetime, timedelta

cloudwatch = boto3.client('cloudwatch')
logs = boto3.client('logs')

# Get cache hit rate
response = logs.start_query(
    logGroupName='/aws/lambda/mcp-incident-responder-prod-AnalysisFunction',
    startTime=int((datetime.now() - timedelta(days=7)).timestamp()),
    endTime=int(datetime.now().timestamp()),
    queryString='''
        fields @timestamp
        | filter @message like /cache/
        | stats count(*) as total,
                sum(@message like /Using cached/) as hits
        | fields hits / total * 100 as hit_rate
    '''
)

# Wait for query and get results
# Adjust cache TTL based on hit rate
```

## Cost Management

### Monthly Cost Report

```bash
#!/bin/bash
# monthly-cost-report.sh

START_DATE=$(date -d '1 month ago' +%Y-%m-%d)
END_DATE=$(date +%Y-%m-%d)

echo "=== Monthly Cost Report: $START_DATE to $END_DATE ==="

# Get costs by service
aws ce get-cost-and-usage \
  --time-period Start=$START_DATE,End=$END_DATE \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE \
  --filter file://cost-filter.json \
  --query 'ResultsByTime[0].Groups[].[Keys[0],Metrics.BlendedCost.Amount]' \
  --output table

# Estimate Anthropic costs (from logs)
ANALYSIS_COUNT=$(aws logs insights query-logs \
  --log-group-name /aws/lambda/mcp-incident-responder-prod-AnalysisFunction \
  --start-time $(date -d '1 month ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'filter @message like /Claude analysis/ | stats count()' \
  --query 'results[0][0].value' \
  --output text)

ANTHROPIC_COST=$(echo "$ANALYSIS_COUNT * 0.03" | bc)
echo "Estimated Anthropic API Cost: \$$ANTHROPIC_COST"
```

### Cost Optimization Checklist

- [ ] Cache hit rate > 60%
- [ ] Lambda memory optimized
- [ ] DynamoDB using on-demand billing
- [ ] Old alerts cleaned up (90-day retention)
- [ ] Log retention set to 30 days
- [ ] No provisioned concurrency (unless needed)
- [ ] Alert throttling for noisy sources
- [ ] Using tiered Claude models

## Backup and Recovery

### Backup Procedure

```bash
#!/bin/bash
# backup.sh - Run daily

BACKUP_BUCKET="mcp-responder-backups"
DATE=$(date +%Y-%m-%d)

# 1. Export DynamoDB tables
aws dynamodb export-table-to-point-in-time \
  --table-arn arn:aws:dynamodb:region:account:table/alerts \
  --s3-bucket $BACKUP_BUCKET \
  --s3-prefix dynamodb-exports/$DATE/

# 2. Backup configuration
aws cloudformation describe-stacks \
  --stack-name mcp-incident-responder-prod \
  --output json > $BACKUP_BUCKET/config/$DATE/stack.json

# 3. Backup Lambda code
aws lambda get-function \
  --function-name mcp-incident-responder-prod-AnalysisFunction \
  --query 'Code.Location' \
  --output text | \
  xargs wget -O $BACKUP_BUCKET/code/$DATE/analysis-function.zip
```

### Disaster Recovery

```bash
# 1. Deploy to new region
aws cloudformation create-stack \
  --stack-name mcp-incident-responder-prod \
  --template-body file://template.yaml \
  --region us-west-2

# 2. Restore DynamoDB from backup
aws dynamodb restore-table-from-backup \
  --target-table-name alerts \
  --backup-arn arn:aws:dynamodb:region:account:table/alerts/backup/latest

# 3. Update DNS/API Gateway to point to new region
```

---

## Emergency Contacts

- **On-Call Engineer**: [Contact Info]
- **AWS Support**: [Case Number]
- **Anthropic Support**: support@anthropic.com
- **Escalation Path**: [Details]

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-10-22 | Initial version | System Architect |

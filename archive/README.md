# MCP Intelligent Incident Response System

An automated incident response system that receives alerts from CloudWatch and other sources, performs intelligent AI-powered analysis using Claude, and delivers actionable reports to Slack, Jira, and email.

## Architecture Overview

```
CloudWatch/Alerts → API Gateway → Lambda (Reception)
                                      ↓
                                    SQS Queue
                                      ↓
                         Lambda (Analysis - Claude AI)
                                      ↓
                                  DynamoDB
                                      ↓
                                  SQS Queue
                                      ↓
                         Lambda (Distribution)
                            ↓         ↓        ↓
                         Slack     Jira     Email
```

## Features

### Intelligent Analysis
- AI-powered error analysis using Claude Sonnet 4
- Automatic severity assessment
- Root cause hypothesis generation
- Impact assessment
- Actionable remediation steps
- Pattern recognition from historical data
- Context gathering from logs and metrics

### Multi-Channel Distribution
- **Slack**: Rich formatted messages with action buttons
- **Jira**: Automatic incident ticket creation (optional)
- **Email**: HTML and text formats (optional)

### Scalability & Reliability
- Serverless architecture with auto-scaling
- SQS queues for reliable message processing
- Dead letter queues for failed messages
- Analysis caching to reduce API costs
- CloudWatch monitoring and alarms

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured
- AWS SAM CLI installed
- Python 3.12+
- Anthropic API key
- Slack webhook URL
- (Optional) Jira API credentials
- (Optional) SES configured for email

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd mcp-incident-responder
```

### 2. Configure Credentials

Create a `.env` file:

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
ANTHROPIC_API_KEY=sk-ant-api03-...
AWS_REGION=us-east-1

# Optional
JIRA_URL=https://your-domain.atlassian.net
JIRA_API_TOKEN=your-jira-token
JIRA_PROJECT=INC
EMAIL_FROM=alerts@your-domain.com
EMAIL_TO=oncall@your-domain.com,team@your-domain.com
```

### 3. Deploy

First, create an S3 bucket for deployment artifacts:

```bash
aws s3 mb s3://your-deployment-bucket
```

Then deploy:

```bash
chmod +x deploy.sh
./deploy.sh \
  --bucket your-deployment-bucket \
  --environment dev \
  --slack-webhook "$SLACK_WEBHOOK_URL" \
  --anthropic-key "$ANTHROPIC_API_KEY"
```

### 4. Configure CloudWatch

After deployment, note the webhook URL from the output. Configure CloudWatch to send alerts:

#### Option A: CloudWatch Alarms via SNS

1. Create an SNS topic:
```bash
aws sns create-topic --name incident-alerts
```

2. Subscribe the webhook endpoint to SNS:
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:region:account:incident-alerts \
  --protocol https \
  --notification-endpoint <webhook-url>
```

3. Configure CloudWatch alarms to publish to this SNS topic

#### Option B: CloudWatch Logs Subscription Filter

```bash
aws logs put-subscription-filter \
  --log-group-name /aws/lambda/your-function \
  --filter-name error-filter \
  --filter-pattern "ERROR" \
  --destination-arn <webhook-lambda-arn>
```

#### Option C: EventBridge Rule

Create an EventBridge rule that forwards CloudWatch events to the webhook endpoint.

## Testing

### Send a Test Alert

```bash
curl -X POST <webhook-url> \
  -H "Content-Type: application/json" \
  -H "x-api-key: <your-api-key>" \
  -d '{
    "source": "test",
    "title": "Test Application Error",
    "message": "NullPointerException in UserService.java:42\n  at com.example.UserService.getUser()\n  at com.example.UserController.handleRequest()",
    "severity": "HIGH",
    "timestamp": "2025-10-22T10:30:00Z"
  }'
```

### View Results

1. Check CloudWatch Logs for each Lambda function
2. Check DynamoDB tables for stored alerts
3. Verify Slack message was received
4. Check Jira for created ticket (if enabled)
5. Check email inbox (if enabled)

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| ANTHROPIC_API_KEY | Yes | Claude API key for analysis |
| SLACK_WEBHOOK_URL | Yes | Slack webhook for notifications |
| JIRA_ENABLED | No | Enable Jira integration (true/false) |
| JIRA_URL | No | Jira instance URL |
| JIRA_API_TOKEN | No | Jira API token |
| JIRA_PROJECT | No | Jira project key |
| EMAIL_ENABLED | No | Enable email notifications (true/false) |
| EMAIL_FROM | No | Sender email address |
| EMAIL_TO | No | Recipient emails (comma-separated) |

### Severity Levels

- **CRITICAL**: Immediate attention required, system down
- **HIGH**: Major functionality impacted, requires urgent response
- **MEDIUM**: Degraded performance or warnings
- **LOW**: Informational or minor issues

## System Components

### 1. Alert Reception Layer
- **Handler**: `src/reception/handler.py`
- **Function**: Receives and normalizes alerts from various sources
- **Output**: Normalized alert to SQS processing queue

### 2. Analysis Engine
- **Handler**: `src/analysis/handler.py`
- **Function**: Uses Claude AI to analyze alerts
- **Features**:
  - Context gathering from logs and historical data
  - Root cause analysis
  - Impact assessment
  - Remediation suggestions
  - Analysis caching for similar errors
- **Output**: Analyzed report to distribution queue

### 3. Distribution Layer
- **Handler**: `src/distribution/handler.py`
- **Function**: Sends reports to configured channels
- **Channels**:
  - Slack (rich formatted messages)
  - Jira (incident tickets)
  - Email (HTML and text)

### 4. Data Storage
- **Alerts Table**: Stores all alerts and analysis results
- **Analysis Cache Table**: Caches analysis for similar errors (TTL: 24h)

## Advanced Features

### Pattern Recognition

The system tracks historical patterns:
- Frequency of similar errors
- First and last occurrence
- Trend analysis

### Analysis Caching

Similar errors within 1 hour use cached analysis to:
- Reduce API costs
- Improve response time
- Maintain consistency

### Dead Letter Queue

Failed messages are sent to DLQ for investigation:
```bash
aws sqs receive-message \
  --queue-url <dlq-url> \
  --max-number-of-messages 10
```

## Monitoring

### CloudWatch Metrics

Key metrics to monitor:
- Lambda invocation count and errors
- SQS queue depth
- DLQ message count
- DynamoDB read/write capacity
- API Gateway 4xx/5xx errors

### CloudWatch Alarms

The system includes a pre-configured alarm for DLQ messages. Add more as needed:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name high-queue-depth \
  --metric-name ApproximateNumberOfMessagesVisible \
  --namespace AWS/SQS \
  --statistic Average \
  --period 300 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold
```

## Cost Optimization

### Expected Costs (at 1000 alerts/month)

- **Lambda**: ~$5-10 (depends on execution time)
- **DynamoDB**: ~$5 (pay-per-request pricing)
- **SQS**: ~$1
- **API Gateway**: ~$3.50
- **Anthropic API**: ~$15-30 (depends on usage and caching effectiveness)

**Total**: ~$30-50/month

### Cost Saving Tips

1. **Enable analysis caching** (already implemented)
2. **Adjust Lambda memory** based on actual usage
3. **Use reserved capacity** for DynamoDB if usage is predictable
4. **Implement alert throttling** for noisy alerts
5. **Batch processing** for low-priority alerts

## Troubleshooting

### Alerts Not Being Processed

1. Check API Gateway logs
2. Verify webhook authentication
3. Check Lambda execution logs
4. Verify SQS queue configuration

### Analysis Failures

1. Check Anthropic API key is valid
2. Verify Lambda has sufficient memory (1024 MB recommended)
3. Check Lambda timeout (900s recommended)
4. Review CloudWatch Logs for specific errors

### Distribution Failures

1. Verify Slack webhook URL is correct
2. Check Jira credentials and permissions
3. Verify SES is configured for email
4. Check distribution Lambda logs

### High Costs

1. Review Anthropic API usage
2. Check if caching is working correctly
3. Look for alert storms or loops
4. Consider implementing rate limiting

## Development

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run unit tests
python -m pytest tests/

# Local SAM testing
sam local invoke AnalysisFunction -e tests/events/alert.json
```

### Adding New Alert Sources

1. Add normalization logic in `src/reception/handler.py`
2. Update the `normalize_alert()` function
3. Test with sample payloads

### Customizing Analysis Prompts

Edit the `get_system_prompt()` function in `src/analysis/handler.py` to customize Claude's analysis behavior.

### Adding New Distribution Channels

1. Create a new function in `src/distribution/handler.py`
2. Add configuration for the new channel
3. Update the `distribute_report()` function to call your new handler

## Security Best Practices

1. **API Keys**: Store in AWS Secrets Manager or SSM Parameter Store
2. **Webhook Authentication**: Use API Gateway API keys
3. **IAM Roles**: Follow least-privilege principle
4. **VPC**: Consider deploying Lambdas in VPC for private resources
5. **Encryption**: Enable encryption at rest for DynamoDB
6. **Audit**: Enable CloudTrail for API call logging

## Roadmap

### Phase 2 - Enhanced Intelligence
- [ ] Machine learning for pattern recognition
- [ ] Automated remediation for known issues
- [ ] Correlation with deployment events
- [ ] Predictive alerting

### Phase 3 - Advanced Integrations
- [ ] PagerDuty integration
- [ ] Microsoft Teams support
- [ ] ServiceNow integration
- [ ] Grafana webhook support

### Phase 4 - Operational Excellence
- [ ] Alert deduplication
- [ ] Auto-escalation rules
- [ ] Runbook automation
- [ ] Post-mortem report generation

## Support

For issues and questions:
1. Check CloudWatch Logs
2. Review this documentation
3. Check AWS service health
4. Verify all credentials are valid

## License

[Your License Here]

## Contributing

Contributions welcome! Please submit pull requests or open issues for bugs and feature requests.

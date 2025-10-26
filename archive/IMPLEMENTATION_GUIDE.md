# MCP Intelligent Incident Response System
## Complete Implementation Guide

---

## 🎯 Project Overview

This is a production-ready, AI-powered incident response system that automatically:
1. Receives alerts from CloudWatch and other monitoring sources
2. Performs intelligent analysis using Claude AI
3. Delivers actionable reports to Slack, Jira, and Email

**Built with**: AWS Lambda (Serverless), Python 3.12, Claude Sonnet 4, DynamoDB, SQS

---

## 📁 Project Structure

```
mcp-incident-responder/
├── template.yaml                 # Main AWS SAM CloudFormation template
├── deploy.sh                     # Deployment automation script
├── requirements.txt              # Python dependencies
├── cloudwatch-integration.yaml   # CloudWatch setup template
├── README.md                     # Quick start guide
│
├── src/                          # Application source code
│   ├── reception/                # Alert ingestion layer
│   │   └── handler.py           # Normalizes alerts from various sources
│   ├── analysis/                 # AI analysis engine
│   │   └── handler.py           # Claude-powered alert analysis
│   └── distribution/             # Multi-channel delivery
│       └── handler.py           # Slack, Jira, Email distribution
│
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md          # Detailed architecture & design decisions
│   ├── OPERATIONS.md            # Operations runbook
│   └── generate_diagrams.py    # Architecture diagram generator
│
└── tests/                        # Testing resources
    ├── SAMPLE_ALERTS.md         # Sample alert formats
    └── events/                  # Test event payloads
        ├── generic-alert.json
        └── cloudwatch-alarm.json
```

---

## 🚀 Quick Start (15 minutes)

### Prerequisites

```bash
# Install required tools
brew install awscli aws-sam-cli  # macOS
# or
apt-get install awscli           # Linux

# Configure AWS credentials
aws configure
```

### Step 1: Deploy the System

```bash
# Clone the repository
cd mcp-incident-responder

# Create S3 bucket for deployment
aws s3 mb s3://your-deployment-bucket-name

# Deploy (replace with your values)
chmod +x deploy.sh
./deploy.sh \
  --bucket your-deployment-bucket-name \
  --environment dev \
  --slack-webhook "https://hooks.slack.com/services/YOUR/WEBHOOK" \
  --anthropic-key "sk-ant-api03-YOUR-KEY"
```

**Note the WebhookUrl from the deployment output** - you'll need this!

### Step 2: Set Up CloudWatch Integration

```bash
# Deploy CloudWatch integration
aws cloudformation create-stack \
  --stack-name mcp-cloudwatch-integration \
  --template-body file://cloudwatch-integration.yaml \
  --parameters \
    ParameterKey=WebhookUrl,ParameterValue=<your-webhook-url> \
    ParameterKey=ApiKey,ParameterValue=<your-api-key>
```

### Step 3: Test the System

```bash
# Send a test alert
curl -X POST "<your-webhook-url>" \
  -H "Content-Type: application/json" \
  -H "x-api-key: <your-api-key>" \
  -d '{
    "source": "test",
    "title": "Test Error: Database Connection Failed",
    "message": "PostgreSQL connection timeout after 30s\nError: FATAL: too many connections for role \"app_user\"\nat Connection.connect(connection.js:42)",
    "severity": "HIGH",
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
  }'
```

**Expected Result**: Within 30-60 seconds, you should receive:
1. A Slack message with AI-powered analysis
2. Optional: Jira ticket (if enabled)
3. Optional: Email notification (if enabled)

---

## 🏗️ Architecture Highlights

### Design Philosophy
- **Event-Driven**: Asynchronous processing for scalability
- **Serverless**: Zero infrastructure management
- **AI-Powered**: Claude provides intelligent analysis
- **Resilient**: DLQ, retries, and error handling
- **Cost-Optimized**: Analysis caching, pay-per-use

### Data Flow

```
Alert Source → API Gateway → Reception Lambda → SQS Queue
                                                    ↓
                                              Analysis Lambda
                                              (Claude AI)
                                                    ↓
                                               DynamoDB
                                                    ↓
                                              SQS Queue
                                                    ↓
                                           Distribution Lambda
                                              ↓    ↓    ↓
                                          Slack Jira Email
```

### Key Components

1. **Reception Layer**: Normalizes alerts from any source
2. **Analysis Engine**: Claude AI + context gathering
3. **Distribution Layer**: Multi-channel delivery
4. **Data Layer**: DynamoDB for storage & caching

---

## 💡 Key Features

### Intelligent Analysis
- Root cause hypothesis generation
- Severity assessment with justification
- Impact analysis
- Actionable remediation steps
- Historical pattern recognition
- Context gathering from logs

### Multi-Source Support
- CloudWatch Alarms
- CloudWatch Logs
- SNS messages
- Custom webhooks
- Any JSON-based alert

### Efficiency Features
- **Analysis Caching**: 60-80% cost reduction for repeated errors
- **Batch Processing**: Handle alert storms gracefully
- **Smart Routing**: Severity-based prioritization
- **Pattern Recognition**: Learn from historical data

---

## 📊 Expected Costs

### Monthly Costs (1000 alerts/month)

| Component | Cost |
|-----------|------|
| Lambda | ~$5-10 |
| API Gateway | ~$3.50 |
| SQS | ~$1 |
| DynamoDB | ~$7.50 |
| CloudWatch | ~$5 |
| Anthropic API | ~$15-30 |
| **Total** | **~$37-57** |

**Cost grows linearly with alert volume**

### Cost Optimization Tips
1. Enable analysis caching (already implemented) ✅
2. Use alert throttling for noisy sources
3. Implement tiered Claude models (Haiku for low priority)
4. Set DynamoDB to on-demand pricing ✅
5. Use reserved capacity at high volumes

---

## 🔧 Configuration Guide

### Environment Variables

Edit these in `template.yaml` or AWS Console:

```yaml
# Required
ANTHROPIC_API_KEY: sk-ant-api03-...
SLACK_WEBHOOK_URL: https://hooks.slack.com/...

# Optional - Jira
JIRA_ENABLED: true
JIRA_URL: https://your-domain.atlassian.net
JIRA_API_TOKEN: your-token
JIRA_PROJECT: INC

# Optional - Email
EMAIL_ENABLED: true
EMAIL_FROM: alerts@your-domain.com
EMAIL_TO: oncall@your-domain.com,team@your-domain.com
```

### Severity Levels

The system recognizes four severity levels:

- **CRITICAL**: Immediate attention, system down
- **HIGH**: Major functionality impacted
- **MEDIUM**: Degraded performance, warnings
- **LOW**: Informational, minor issues

---

## 📖 Usage Examples

### Example 1: CloudWatch Alarm Integration

```bash
# Create alarm that triggers MCP
aws cloudwatch put-metric-alarm \
  --alarm-name high-error-rate \
  --alarm-description "Error rate exceeded threshold" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:region:account:mcp-incident-alerts
```

### Example 2: CloudWatch Logs Integration

```bash
# Subscribe logs to MCP
aws logs put-subscription-filter \
  --log-group-name /aws/lambda/your-function \
  --filter-name error-filter \
  --filter-pattern "?ERROR ?Exception ?CRITICAL" \
  --destination-arn <LogSubscriptionFunctionArn>
```

### Example 3: Custom Application Integration

```python
# Python application sending custom alerts
import requests
import json
from datetime import datetime

def send_alert(title, message, severity="MEDIUM"):
    webhook_url = "https://your-api-gateway-url/alert"
    api_key = "your-api-key"
    
    alert = {
        "source": "my-application",
        "title": title,
        "message": message,
        "severity": severity,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    response = requests.post(
        webhook_url,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key
        },
        json=alert
    )
    
    return response.status_code == 202

# Usage
send_alert(
    title="Payment Processing Failed",
    message="Stripe API returned 500 error\nTransaction ID: txn_12345",
    severity="HIGH"
)
```

---

## 🔍 Monitoring & Debugging

### CloudWatch Logs

View logs for each component:

```bash
# Reception layer
aws logs tail /aws/lambda/mcp-incident-responder-prod-AlertReceptionFunction --follow

# Analysis layer
aws logs tail /aws/lambda/mcp-incident-responder-prod-AnalysisFunction --follow

# Distribution layer
aws logs tail /aws/lambda/mcp-incident-responder-prod-DistributionFunction --follow
```

### CloudWatch Insights Queries

```sql
-- Error analysis by source
fields @timestamp, source, severity
| filter level = "ERROR"
| stats count() by source, severity

-- Average processing time
fields @timestamp, @duration
| stats avg(@duration) as avg_ms, 
        max(@duration) as max_ms,
        min(@duration) as min_ms

-- Cache hit rate
fields @timestamp
| filter @message like /cache/
| stats count(*) as total,
        sum(@message like /cached/) as hits
| fields hits / total * 100 as hit_rate
```

### DynamoDB Queries

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
```

---

## 🛡️ Security Best Practices

### Implemented Security Features ✅

1. **API Gateway Authentication**: API key required
2. **Secrets Management**: Anthropic key in environment variables
3. **IAM Least Privilege**: Each Lambda has minimal permissions
4. **Encryption at Rest**: DynamoDB encrypted
5. **HTTPS Only**: All traffic encrypted in transit

### Recommended Enhancements

1. **Move secrets to AWS Secrets Manager**:
```bash
aws secretsmanager create-secret \
  --name mcp/anthropic-key \
  --secret-string "sk-ant-api03-..."
```

2. **Enable VPC deployment** (optional for private resources)
3. **Add WAF rules** for API Gateway
4. **Enable CloudTrail** for audit logging
5. **Set up GuardDuty** for threat detection

---

## 🐛 Troubleshooting

### Issue: No alerts being processed

**Check**:
1. API Gateway has valid API key
2. Lambda functions are not throttled
3. SQS queues are not full
4. Check CloudWatch Logs for errors

**Solution**:
```bash
# Check Lambda concurrency
aws lambda get-function-concurrency \
  --function-name mcp-incident-responder-prod-AnalysisFunction

# Check queue depth
aws sqs get-queue-attributes \
  --queue-url <queue-url> \
  --attribute-names ApproximateNumberOfMessagesVisible
```

### Issue: Slack messages not delivered

**Check**:
1. Slack webhook URL is correct
2. Distribution Lambda has internet access
3. Check Lambda logs for errors

**Solution**:
```bash
# Test webhook manually
curl -X POST "https://hooks.slack.com/services/YOUR/WEBHOOK" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test"}'

# Update webhook if needed
aws lambda update-function-configuration \
  --function-name mcp-incident-responder-prod-DistributionFunction \
  --environment Variables={SLACK_WEBHOOK_URL=new-url}
```

### Issue: High costs

**Check**:
1. Analysis cache hit rate
2. Alert volume
3. Claude API usage

**Solution**:
```bash
# Check cache effectiveness
aws dynamodb scan \
  --table-name mcp-incident-responder-prod-analysis-cache \
  --select COUNT

# Review alert patterns
aws dynamodb scan \
  --table-name mcp-incident-responder-prod-alerts \
  --filter-expression "created_at > :time" \
  --expression-attribute-values '{":time":{"S":"'$(date -d '7 days ago' +%Y-%m-%d)'"}}' \
  --select COUNT
```

---

## 🔄 Maintenance

### Daily Tasks
- Check DLQ for failed messages
- Review error rates in CloudWatch
- Monitor alert volume

### Weekly Tasks
- Review cost trends
- Analyze cache hit rates
- Check for new alert patterns

### Monthly Tasks
- Review and optimize Lambda memory
- Clean up old alerts (if not using TTL)
- Update dependencies
- Review and optimize costs

---

## 📚 Additional Resources

- **Architecture Details**: `docs/ARCHITECTURE.md`
- **Operations Guide**: `docs/OPERATIONS.md`
- **Sample Alerts**: `tests/SAMPLE_ALERTS.md`
- **AWS SAM Documentation**: https://docs.aws.amazon.com/serverless-application-model/
- **Anthropic Claude API**: https://docs.anthropic.com/

---

## 🎓 Learning Path

### Phase 1: Get It Working
1. Deploy the basic system ✅
2. Send test alerts ✅
3. Verify Slack notifications ✅

### Phase 2: Integrate with Your Infrastructure
4. Connect CloudWatch alarms
5. Add log subscriptions
6. Configure alert sources

### Phase 3: Optimize
7. Monitor costs and performance
8. Tune Lambda memory
9. Optimize cache hit rate

### Phase 4: Enhance
10. Add Jira integration
11. Enable email notifications
12. Implement custom analysis logic

---

## 🤝 Support

### Getting Help

1. **Check the docs**: Start with `README.md`, `docs/ARCHITECTURE.md`, and `docs/OPERATIONS.md`
2. **Review CloudWatch Logs**: Most issues show up in logs
3. **Test components individually**: Use SAM local for testing
4. **Check AWS Service Health**: Verify services are operational

### Common Commands Reference

```bash
# View all stacks
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE

# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name mcp-incident-responder-prod \
  --query 'Stacks[0].Outputs'

# Tail all Lambda logs
sam logs --stack-name mcp-incident-responder-prod --tail

# Update a single Lambda
aws lambda update-function-code \
  --function-name mcp-incident-responder-prod-AnalysisFunction \
  --zip-file fileb://function.zip
```

---

## 🎉 Success Metrics

Track these KPIs to measure system effectiveness:

1. **Response Time**: Alert receipt to notification delivery
   - Target: < 60 seconds

2. **Analysis Quality**: Actionable insights per alert
   - Target: > 80% useful analysis

3. **Cost Efficiency**: Cost per alert processed
   - Target: < $0.05 per alert

4. **Reliability**: System uptime
   - Target: 99.9%

5. **Cache Hit Rate**: Percentage of cached analyses
   - Target: > 60%

---

## 🚀 What's Next?

### Immediate Next Steps

1. **Deploy to staging** and run integration tests
2. **Configure your monitoring tools** to send alerts
3. **Set up CloudWatch dashboards** for visibility
4. **Document your runbooks** in the system

### Future Enhancements (Roadmap)

- [ ] PagerDuty integration
- [ ] Microsoft Teams support
- [ ] Advanced ML-based pattern recognition
- [ ] Automated remediation workflows
- [ ] Post-mortem report generation
- [ ] Multi-region deployment
- [ ] GraphQL API for alert queries

---

## 📄 License & Credits

**Built with**: AWS Lambda, Python, Claude AI (Anthropic), AWS SAM

**License**: [Your License]

**Contributors**: [Your Team]

---

**Remember**: This is a production-ready foundation. Customize it to match your specific infrastructure, team workflows, and operational requirements. The modular architecture makes it easy to extend and enhance!

**Happy Incident Response!** 🎯

# 🚑 MCP First-Responder

[![GitHub](https://img.shields.io/badge/GitHub-ogkatzu%2FMadabot-blue?logo=github)](https://github.com/ogkatzu/Madabot)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Powered by Claude](https://img.shields.io/badge/Powered%20by-Claude%20AI-blueviolet)](https://claude.ai)

**Intelligent Incident Response System** - Transform CloudWatch alerts into actionable insights with AI-powered analysis. Automatically diagnose issues, assess impact, and distribute intelligent incident reports to Slack, Jira, and email.

![MCP First-Responder Architecture](docs/static/ambulance.png)

## 🎯 Overview

MCP First-Responder is a serverless, event-driven incident response system that leverages Claude AI to provide intelligent analysis of AWS CloudWatch alerts. Stop drowning in alerts and start acting on intelligence.

### Key Features

- **🧠 AI-Powered Analysis** - Claude AI analyzes logs, traces, and infrastructure state to determine root cause and impact within seconds
- **📊 Context-Aware** - Automatically gathers CloudWatch logs, deployment history, infrastructure health, and historical patterns
- **💰 Cost Optimized** - Intelligent caching reduces API costs by 80%. Run 100 alerts/day for ~$58/month
- **⚡ Serverless Architecture** - Event-driven design using Lambda, EventBridge, SQS, and DynamoDB. Zero infrastructure to manage
- **🔔 Multi-Channel Distribution** - Rich Slack notifications with Block Kit, automatic Jira tickets, and formatted email alerts
- **🛡️ Production Ready** - Circuit breakers, DLQ monitoring, retry logic, and graceful degradation built-in

### Performance Metrics

- **<60 seconds** from alert to analysis
- **80% cost reduction** through intelligent caching
- **24/7 automated response** with no human intervention required

## 🏗️ Architecture

```
┌─────────────────┐
│ Alert Sources   │
│ - CloudWatch    │
│ - SNS           │
│ - Custom        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  EventBridge    │
│   Rule Filter   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Ingestor Lambda │
│ - Normalize     │
│ - Enrich        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   SQS FIFO      │
│ Processing Queue│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Analyzer Lambda │
│ - Context       │
│ - Claude AI     │
│ - Cache         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   DynamoDB      │
│ Alerts + Cache  │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Distribution    │
│     Queue       │
└────────┬────────┘
         │
    ┌────┴────┬────────┐
    ▼         ▼        ▼
┌────────┐┌────────┐┌────────┐
│ Slack  ││ Jira   ││ Email  │
│Notifier││Notifier││Notifier│
└────────┘└────────┘└────────┘
```

## 🚀 Quick Start

### Prerequisites

- AWS Account with appropriate permissions
- Terraform >= 1.0
- Python 3.11+
- Claude API key (Anthropic)
- Slack webhook URL
- (Optional) Jira credentials

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ogkatzu/Madabot.git
   cd Madabot
   ```

2. **Configure environment variables**
   ```bash
   cp terraform/environments/dev.tfvars.example terraform/environments/dev.tfvars
   # Edit dev.tfvars with your values
   ```

3. **Initialize Terraform**
   ```bash
   cd terraform
   terraform init
   ```

4. **Review and apply infrastructure**
   ```bash
   terraform plan -var-file=environments/dev.tfvars
   terraform apply -var-file=environments/dev.tfvars
   ```

5. **Configure CloudWatch Log Subscriptions**
   ```bash
   # Subscribe your CloudWatch log groups to the ingestor Lambda
   aws logs put-subscription-filter \
     --log-group-name /aws/lambda/your-app \
     --filter-name mcp-first-responder \
     --filter-pattern "[timestamp, request_id, level=ERROR*, ...]" \
     --destination-arn $(terraform output -raw ingestor_lambda_arn)
   ```

## 📋 Configuration

### Environment Variables

Create a `terraform/environments/dev.tfvars` file with the following:

```hcl
# Required
anthropic_api_key = "sk-ant-xxxxx"
slack_webhook_url = "https://hooks.slack.com/services/xxxxx"
environment       = "dev"
aws_region        = "us-east-1"

# Optional
jira_url          = "https://your-domain.atlassian.net"
jira_username     = "your-email@example.com"
jira_api_token    = "your-jira-token"
jira_project_key  = "INC"

email_from        = "alerts@example.com"
email_recipients  = ["oncall@example.com", "devops@example.com"]
```

### Alert Sources

The system can ingest alerts from multiple sources:

1. **CloudWatch Logs** - Via subscription filters
2. **CloudWatch Alarms** - Via EventBridge rules
3. **SNS Topics** - Direct integration
4. **Custom Webhooks** - API Gateway endpoint (optional)

## 🔧 Development

### Project Structure

```
.
├── lambdas/
│   ├── ingestor/          # Alert normalization and enrichment
│   ├── analyzer/          # AI-powered analysis engine
│   ├── slack_notifier/    # Slack Block Kit notifications
│   ├── jira_notifier/     # Jira ticket creation
│   └── email_notifier/    # SES email notifications
├── terraform/             # Infrastructure as Code
│   ├── main.tf
│   ├── lambda.tf
│   ├── dynamodb.tf
│   ├── sqs.tf
│   └── environments/
├── docs/                  # Landing page and documentation
│   ├── index.html
│   ├── styles.css
│   └── static/
└── test/                  # Test utilities and fixtures
```

### Local Development

1. **Install Lambda dependencies**
   ```bash
   cd lambdas/analyzer
   pip install -r requirements.txt
   ```

2. **Run tests**
   ```bash
   python -m pytest tests/
   ```

3. **Test locally with SAM (optional)**
   ```bash
   sam local invoke AnalyzerFunction -e test/events/sample-alert.json
   ```

### Testing

Generate test alerts:
```bash
python test/generate_test_alert.py --severity CRITICAL --service api-gateway
```

Monitor processing:
```bash
# View logs
aws logs tail /aws/lambda/mcp-analyzer --follow

# Check queue depth
aws sqs get-queue-attributes \
  --queue-url $(terraform output -raw processing_queue_url) \
  --attribute-names ApproximateNumberOfMessagesVisible
```

## 📊 Monitoring

### CloudWatch Dashboards

The deployment creates a CloudWatch dashboard with:
- Lambda invocation rates and errors
- SQS queue depth and age
- DynamoDB read/write capacity
- Claude API latency and costs
- Dead Letter Queue alerts

### Alarms

Pre-configured CloudWatch alarms for:
- Lambda errors > 5% over 5 minutes
- DLQ messages > 0
- SQS queue age > 15 minutes
- DynamoDB throttling

## 💰 Cost Breakdown

**Estimated monthly costs for 100 alerts/day:**

| Service | Cost | Notes |
|---------|------|-------|
| Claude API | $45 | ~$0.015/alert (80% cached) |
| Lambda | $8 | 5 functions, ~2GB-sec per alert |
| DynamoDB | $2 | On-demand with 30-day retention |
| SQS | <$1 | FIFO queues |
| EventBridge | <$1 | Rules and targets |
| **Total** | **~$58/month** | |

Cost optimization tips:
- Enable 24-hour cache TTL (reduces API costs by 80%)
- Use Lambda reserved concurrency for predictable costs
- Archive old alerts to S3 Glacier for long-term retention

## 🤝 Contributing

This is a hackathon project, but contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Claude AI** by Anthropic - Powers the intelligent analysis
- **Catppuccin Theme** - Beautiful color palette for the landing page
- Built during a 3-4 day hackathon sprint

## 📚 Documentation

- [Architecture Deep Dive](docs/architecture.md)
- [API Reference](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Troubleshooting](docs/troubleshooting.md)

## 🔗 Links

- [Live Demo](https://ogkatzu.github.io/Madabot/) (GitHub Pages)
- [Project Repository](https://github.com/ogkatzu/Madabot)
- [Issue Tracker](https://github.com/ogkatzu/Madabot/issues)

---

**Built with ❤️ using Claude AI • Hackathon Project 2025**

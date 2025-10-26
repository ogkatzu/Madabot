# Sample Alert Payloads for Testing

This directory contains various sample alert formats to test the system.

## 1. Simple Generic Alert

```json
{
  "source": "monitoring",
  "title": "High CPU Usage Detected",
  "message": "CPU usage exceeded 90% threshold on web-server-01",
  "severity": "HIGH",
  "timestamp": "2025-10-22T10:30:00Z"
}
```

## 2. CloudWatch Alarm

```json
{
  "AlarmName": "HighErrorRate",
  "AlarmDescription": "Error rate exceeded 5% threshold",
  "AWSAccountId": "123456789012",
  "NewStateValue": "ALARM",
  "NewStateReason": "Threshold Crossed: 1 datapoint [8.5] was greater than the threshold (5.0).",
  "StateChangeTime": "2025-10-22T10:30:00.000Z",
  "Region": "us-east-1",
  "OldStateValue": "OK",
  "Trigger": {
    "MetricName": "ErrorRate",
    "Namespace": "AWS/ApplicationELB",
    "StatisticType": "Statistic",
    "Statistic": "AVERAGE",
    "Unit": "Percent",
    "Dimensions": [
      {
        "name": "LoadBalancer",
        "value": "app/my-load-balancer/50dc6c495c0c9188"
      }
    ],
    "Period": 300,
    "EvaluationPeriods": 1,
    "ComparisonOperator": "GreaterThanThreshold",
    "Threshold": 5.0
  }
}
```

## 3. CloudWatch Logs with Exception

```json
{
  "logGroup": "/aws/lambda/UserService",
  "logStream": "2025/10/22/[$LATEST]abcd1234",
  "logEvents": [
    {
      "id": "37055058788431886638277291928716358308398571359196758016",
      "timestamp": 1729592400000,
      "message": "ERROR - NullPointerException in UserService.java:42\n  at com.example.UserService.getUser(UserService.java:42)\n  at com.example.UserController.handleRequest(UserController.java:28)\n  at sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)\nCaused by: Database connection timeout after 30 seconds"
    },
    {
      "id": "37055058788431886638277291928716358308398571359196758017",
      "timestamp": 1729592401000,
      "message": "ERROR - Failed to process user request for userId=12345"
    }
  ]
}
```

## 4. SNS Message Format

```json
{
  "Records": [
    {
      "EventSource": "aws:sns",
      "EventVersion": "1.0",
      "EventSubscriptionArn": "arn:aws:sns:us-east-1:123456789012:incident-alerts:abc123",
      "Sns": {
        "Type": "Notification",
        "MessageId": "abc-123-def-456",
        "TopicArn": "arn:aws:sns:us-east-1:123456789012:incident-alerts",
        "Subject": "Database Connection Pool Exhausted",
        "Message": "{\"source\":\"rds\",\"title\":\"Database Connection Pool Exhausted\",\"message\":\"All database connections in use. Max connections: 100. Active: 100. Waiting: 45.\",\"severity\":\"CRITICAL\",\"timestamp\":\"2025-10-22T10:30:00Z\"}",
        "Timestamp": "2025-10-22T10:30:00.000Z"
      }
    }
  ]
}
```

## 5. Application Error with Stack Trace

```json
{
  "source": "application",
  "title": "Uncaught Exception in Payment Service",
  "message": "java.lang.OutOfMemoryError: Java heap space\n  at com.example.PaymentProcessor.processPayment(PaymentProcessor.java:156)\n  at com.example.OrderService.completeOrder(OrderService.java:89)\n  at com.example.CheckoutController.checkout(CheckoutController.java:45)\n\nHeap Dump Analysis:\n- Used: 3.8 GB / 4.0 GB\n- Objects retained: PaymentRequest (2.1 GB), TransactionLog (1.2 GB)\n- GC time: 95% (indicating memory pressure)",
  "severity": "CRITICAL",
  "timestamp": "2025-10-22T10:30:00Z",
  "metadata": {
    "service": "payment-service",
    "environment": "production",
    "instance": "i-0abc123def456",
    "version": "2.4.1"
  }
}
```

## 6. Security Alert

```json
{
  "source": "security",
  "title": "Multiple Failed Login Attempts Detected",
  "message": "Detected 25 failed login attempts from IP 203.0.113.45 in the last 5 minutes\n\nAttempted usernames:\n- admin\n- root\n- administrator\n- user\n\nLast attempt: 2025-10-22T10:30:00Z\nSource Country: Unknown\nBlocked: Yes",
  "severity": "HIGH",
  "timestamp": "2025-10-22T10:30:00Z",
  "metadata": {
    "source_ip": "203.0.113.45",
    "attack_type": "brute_force",
    "blocked": true
  }
}
```

## 7. Infrastructure Alert

```json
{
  "source": "infrastructure",
  "title": "Disk Space Critical on Database Server",
  "message": "Disk usage on /dev/sda1 has reached 95%\n\nDetails:\n- Total: 500 GB\n- Used: 475 GB\n- Available: 25 GB\n- Largest directories:\n  - /var/lib/postgresql: 350 GB\n  - /var/log: 85 GB\n  - /tmp: 40 GB\n\nAuto-cleanup failed. Manual intervention required.",
  "severity": "CRITICAL",
  "timestamp": "2025-10-22T10:30:00Z",
  "metadata": {
    "hostname": "db-primary-01",
    "filesystem": "/dev/sda1",
    "mount_point": "/",
    "usage_percent": 95
  }
}
```

## 8. Performance Degradation

```json
{
  "source": "apm",
  "title": "API Response Time Degradation",
  "message": "P95 response time for /api/users endpoint increased from 150ms to 2500ms\n\nMetrics:\n- P50: 1800ms (normal: 100ms)\n- P95: 2500ms (normal: 150ms)\n- P99: 4200ms (normal: 300ms)\n- Error rate: 0.5%\n- Request count: 15,000 req/min\n\nAffected timeframe: Last 15 minutes\nPotential cause: Database query N+1 problem detected",
  "severity": "HIGH",
  "timestamp": "2025-10-22T10:30:00Z",
  "metadata": {
    "endpoint": "/api/users",
    "p95_latency": 2500,
    "normal_p95": 150,
    "service": "user-api"
  }
}
```

## Testing Commands

### Test via curl:

```bash
# Get the API key first
API_KEY=$(aws apigateway get-api-keys --query 'items[0].id' --output text)
API_KEY_VALUE=$(aws apigateway get-api-key --api-key $API_KEY --include-value --query 'value' --output text)

# Get webhook URL from CloudFormation outputs
WEBHOOK_URL=$(aws cloudformation describe-stacks \
  --stack-name mcp-incident-responder-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`WebhookUrl`].OutputValue' \
  --output text)

# Send test alert
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY_VALUE" \
  -d @tests/sample-alerts/generic-alert.json
```

### Test with SAM Local:

```bash
sam local invoke AlertReceptionFunction \
  --event tests/sample-alerts/cloudwatch-alarm.json
```

### Load Testing:

```bash
# Send 100 alerts rapidly
for i in {1..100}; do
  curl -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY_VALUE" \
    -d @tests/sample-alerts/generic-alert.json &
done
wait
```

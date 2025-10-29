# Test Application for MCP First-Responder

This is a simple Python application that generates logs to CloudWatch Logs to test the MCP First-Responder alert system.

## What It Does

- Generates logs every 30 seconds
- Creates INFO logs for normal operation (2/3 of the time)
- Creates ERROR/CRITICAL/WARNING logs to trigger alerts (1/3 of the time)
- Sends all logs to CloudWatch Logs group: `/aws/test-app`

## Error Scenarios Generated

The application randomly generates these realistic error scenarios:

1. **Database Connection Timeout** - Simulates PostgreSQL connection failures
2. **Out of Memory Error** - Payment processing memory issues
3. **API Timeout** - External service timeouts
4. **High CPU Usage** - Resource exhaustion warnings
5. **S3 Access Denied** - AWS permission errors
6. **Redis Connection Error** - Cache cluster unavailable

## Setup

### 1. Install Dependencies

```bash
cd test
pip install -r requirements.txt
```

Or using a virtual environment:

```bash
cd test
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure AWS Credentials

Make sure you have AWS credentials configured:

```bash
aws configure
```

Or set environment variables:

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
```

### 3. Grant CloudWatch Logs Permissions

Your AWS user/role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:*:log-group:/aws/test-app:*"
    }
  ]
}
```

## Running the Application

```bash
cd test
python test_app.py
```

You should see output like:

```
Starting test application...
Log Group: /aws/test-app
Generating logs every 30 seconds...
Press Ctrl+C to stop

✓ Generated INFO log #1
✓ Generated INFO log #2
✗ Generated ERROR log
✓ Generated INFO log #4
...
```

## Monitoring Alerts

Once the application is running and generating ERROR/CRITICAL logs, you can monitor the MCP First-Responder pipeline:

### 1. Check CloudWatch Logs

```bash
aws logs tail /aws/test-app --follow
```

### 2. Monitor Processing Queue

```bash
task check-queue ENV=dev
```

### 3. Check Analyzer Logs

```bash
task logs-analyzer ENV=dev
```

### 4. Check Slack Notifier Logs

```bash
task logs-notifier ENV=dev
```

### 5. Watch for Slack Notifications

Check your Slack channel for alerts with Gemini AI analysis!

## Adjusting Behavior

You can modify the application behavior by editing `test_app.py`:

- **Change log frequency**: Modify `time.sleep(30)` (line 101)
- **Change error frequency**: Modify `if iteration % 3 == 0:` (line 72)
- **Add new scenarios**: Add entries to the `scenarios` list (lines 44-70)
- **Change log group**: Modify `log_group='/aws/test-app'` (line 20)

## Stopping the Application

Press `Ctrl+C` to gracefully shut down the application. It will flush remaining logs to CloudWatch before exiting.

## Troubleshooting

### "Unable to locate credentials"
- Run `aws configure` to set up your AWS credentials
- Or set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables

### "AccessDeniedException: User is not authorized"
- Your AWS user/role needs `logs:CreateLogGroup`, `logs:CreateLogStream`, and `logs:PutLogEvents` permissions

### Logs not appearing in CloudWatch
- Check AWS region matches (`us-east-1` by default)
- Verify IAM permissions
- Check console output for errors

### Alerts not triggering in MCP First-Responder
- Verify EventBridge rule is monitoring `/aws/test-app` log group
- Update Terraform variable `cloudwatch_log_group_patterns` in `terraform/environments/dev.tfvars`:
  ```hcl
  cloudwatch_log_group_patterns = [
    "/aws/lambda/*",
    "/aws/test-app"
  ]
  ```
- Redeploy: `task apply ENV=dev`

## Clean Up

To stop generating logs and clean up:

1. Stop the application with `Ctrl+C`
2. (Optional) Delete the CloudWatch log group:
   ```bash
   aws logs delete-log-group --log-group-name /aws/test-app
   ```

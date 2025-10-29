import json
import os
import boto3
import urllib3

http = urllib3.PoolManager()
secrets_client = boto3.client('secretsmanager')

def lambda_handler(event, context):
    """Basic Slack notifier"""
    print(f"Event: {json.dumps(event)}")

    # Get Slack webhook from Secrets Manager
    secret_name = os.environ['SLACK_WEBHOOK_SECRET']
    response = secrets_client.get_secret_value(SecretId=secret_name)
    secret_string = response['SecretString']

    # Parse JSON secret (format: {"saar_slack_webhook": "https://..."})
    secret_data = json.loads(secret_string)
    webhook_url = secret_data['saar_slack_webhook']

    # Parse message
    for record in event.get('Records', []):
        body = json.loads(record['body'])

        msg = {
            'text': f"🚨 *Alert Analysis*\n{body.get('analysis', 'No analysis')}"
        }

        http.request(
            'POST',
            webhook_url,
            body=json.dumps(msg),
            headers={'Content-Type': 'application/json'}
        )

    return {'statusCode': 200}

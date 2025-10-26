import json
import os
import boto3
import urllib3

http = urllib3.PoolManager()
ssm = boto3.client('ssm')

def lambda_handler(event, context):
    """Basic Slack notifier"""
    print(f"Event: {json.dumps(event)}")

    # Get Slack webhook from SSM
    webhook_param = os.environ['SLACK_WEBHOOK_URL_PARAM']
    response = ssm.get_parameter(Name=webhook_param, WithDecryption=True)
    webhook_url = response['Parameter']['Value']

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

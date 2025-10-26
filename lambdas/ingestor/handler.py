import json
import os
import boto3

sqs = boto3.client('sqs')

def lambda_handler(event, context):
    """Basic ingestor - sends alerts to SQS"""
    print(f"Event: {json.dumps(event)}")

    queue_url = os.environ['PROCESSING_QUEUE_URL']

    # Simple message format
    message = {
        'alert_id': context.aws_request_id,
        'message': event.get('detail', {}).get('message', 'Test alert'),
        'severity': 'HIGH',
        'source': 'cloudwatch'
    }

    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message),
        MessageGroupId='alerts'
    )

    return {'statusCode': 200, 'body': 'Alert sent'}

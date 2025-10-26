import json
import os
import boto3
import urllib3

http = urllib3.PoolManager()
ssm = boto3.client('ssm')
sqs = boto3.client('sqs')

def lambda_handler(event, context):
    """
    Basic analyzer Lambda to test Gemini API integration
    """
    print(f"Received event: {json.dumps(event)}")

    # Get API key from SSM
    api_key_param = os.environ.get('GOOGLE_API_KEY_PARAM')
    response = ssm.get_parameter(Name=api_key_param, WithDecryption=True)
    api_key = response['Parameter']['Value']

    # Get distribution queue URL
    distribution_queue_url = os.environ.get('DISTRIBUTION_QUEUE_URL')

    # Parse alert from SQS event
    for record in event.get('Records', []):
        body = json.loads(record['body'])
        alert_message = body.get('message', 'Unknown error')

        # Create simple prompt
        prompt = f"""Analyze this alert and provide a brief diagnosis:

Alert: {alert_message}

Provide:
1. Severity (CRITICAL/HIGH/MEDIUM/LOW)
2. Likely cause
3. One recommended action"""

        # Call Gemini REST API
        url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}'

        payload = {
            'contents': [{
                'parts': [{'text': prompt}]
            }]
        }

        resp = http.request(
            'POST',
            url,
            body=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )

        result = json.loads(resp.data.decode('utf-8'))
        print(f"Gemini API Response: {json.dumps(result)}")

        # Check for errors
        if 'error' in result:
            error_msg = result['error'].get('message', 'Unknown error')
            print(f"Gemini API Error: {error_msg}")
            analysis = f"Error calling Gemini: {error_msg}"
        elif 'candidates' in result:
            analysis = result['candidates'][0]['content']['parts'][0]['text']
        else:
            analysis = "No analysis returned from Gemini"

        print(f"Analysis: {analysis}")

        # Send analysis to distribution queue
        distribution_message = {
            'alert_id': body.get('alert_id'),
            'alert': alert_message,
            'analysis': analysis,
            'severity': body.get('severity', 'UNKNOWN'),
            'source': body.get('source', 'unknown'),
            'model': 'gemini-2.5-flash'
        }

        sqs.send_message(
            QueueUrl=distribution_queue_url,
            MessageBody=json.dumps(distribution_message),
            MessageGroupId='analysis'
        )

        print(f"Sent analysis to distribution queue: {distribution_queue_url}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'alert': alert_message,
                'analysis': analysis,
                'model': 'gemini-2.5-flash'
            })
        }

    return {'statusCode': 200, 'body': 'No records processed'}

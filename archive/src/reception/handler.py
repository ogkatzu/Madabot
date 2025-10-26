import json
import os
import boto3
import hashlib
from datetime import datetime
from typing import Dict, Any

sqs = boto3.client('sqs')
QUEUE_URL = os.environ['PROCESSING_QUEUE_URL']


def receive_alert(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Receives alerts from CloudWatch or other sources via webhook.
    Normalizes the alert format and sends to processing queue.
    """
    try:
        # Parse incoming request
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # Normalize alert based on source
        normalized_alert = normalize_alert(body)
        
        # Generate unique alert ID
        normalized_alert['alert_id'] = generate_alert_id(normalized_alert)
        normalized_alert['received_at'] = datetime.utcnow().isoformat()
        
        # Send to processing queue
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(normalized_alert),
            MessageAttributes={
                'severity': {
                    'StringValue': normalized_alert.get('severity', 'UNKNOWN'),
                    'DataType': 'String'
                }
            }
        )
        
        return {
            'statusCode': 202,
            'body': json.dumps({
                'message': 'Alert received and queued for processing',
                'alert_id': normalized_alert['alert_id']
            })
        }
        
    except Exception as e:
        print(f"Error receiving alert: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def normalize_alert(raw_alert: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize alerts from different sources into a common format.
    Supports CloudWatch, custom webhooks, and SNS messages.
    """
    # Check if this is an SNS message
    if 'Records' in raw_alert and raw_alert['Records'][0].get('EventSource') == 'aws:sns':
        return normalize_sns_alert(raw_alert['Records'][0])
    
    # Check if this is a CloudWatch alarm
    if 'AlarmName' in raw_alert:
        return normalize_cloudwatch_alarm(raw_alert)
    
    # Check if this is CloudWatch Logs via subscription filter
    if 'logEvents' in raw_alert:
        return normalize_cloudwatch_logs(raw_alert)
    
    # Default: treat as generic alert
    return normalize_generic_alert(raw_alert)


def normalize_sns_alert(record: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize SNS notification to standard format."""
    sns_message = json.loads(record['Sns']['Message'])
    
    return {
        'source': 'sns',
        'source_id': record['Sns'].get('MessageId'),
        'title': record['Sns'].get('Subject', 'SNS Alert'),
        'message': sns_message if isinstance(sns_message, str) else json.dumps(sns_message),
        'severity': extract_severity(sns_message),
        'timestamp': record['Sns'].get('Timestamp'),
        'raw_data': record
    }


def normalize_cloudwatch_alarm(alarm: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize CloudWatch alarm to standard format."""
    return {
        'source': 'cloudwatch_alarm',
        'source_id': alarm.get('AlarmName'),
        'title': f"CloudWatch Alarm: {alarm.get('AlarmName')}",
        'message': alarm.get('AlarmDescription', alarm.get('NewStateReason', '')),
        'severity': map_alarm_state_to_severity(alarm.get('NewStateValue')),
        'timestamp': alarm.get('StateChangeTime'),
        'metric_name': alarm.get('Trigger', {}).get('MetricName'),
        'namespace': alarm.get('Trigger', {}).get('Namespace'),
        'dimensions': alarm.get('Trigger', {}).get('Dimensions', []),
        'raw_data': alarm
    }


def normalize_cloudwatch_logs(log_data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize CloudWatch Logs to standard format."""
    log_events = log_data.get('logEvents', [])
    
    # Extract error information from log events
    error_messages = []
    for event in log_events:
        message = event.get('message', '')
        if any(keyword in message.lower() for keyword in ['error', 'exception', 'fatal', 'critical']):
            error_messages.append(message)
    
    return {
        'source': 'cloudwatch_logs',
        'source_id': log_data.get('logGroup'),
        'title': f"Log Alert: {log_data.get('logGroup')}",
        'message': '\n'.join(error_messages) if error_messages else '\n'.join([e['message'] for e in log_events[:5]]),
        'severity': 'HIGH' if error_messages else 'MEDIUM',
        'timestamp': datetime.utcnow().isoformat(),
        'log_group': log_data.get('logGroup'),
        'log_stream': log_data.get('logStream'),
        'log_events': log_events,
        'raw_data': log_data
    }


def normalize_generic_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize generic alert format."""
    return {
        'source': alert.get('source', 'generic'),
        'source_id': alert.get('id', alert.get('alert_id')),
        'title': alert.get('title', alert.get('subject', 'Alert')),
        'message': alert.get('message', alert.get('description', '')),
        'severity': alert.get('severity', extract_severity(alert)),
        'timestamp': alert.get('timestamp', datetime.utcnow().isoformat()),
        'raw_data': alert
    }


def extract_severity(data: Any) -> str:
    """Extract or infer severity from alert data."""
    if isinstance(data, dict):
        severity = data.get('severity', data.get('priority', '')).upper()
        if severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            return severity
        
        # Check message content for severity indicators
        message = str(data.get('message', data.get('description', ''))).lower()
        if any(word in message for word in ['critical', 'fatal', 'emergency']):
            return 'CRITICAL'
        elif any(word in message for word in ['error', 'exception', 'failed']):
            return 'HIGH'
        elif any(word in message for word in ['warning', 'warn']):
            return 'MEDIUM'
    
    return 'MEDIUM'


def map_alarm_state_to_severity(state: str) -> str:
    """Map CloudWatch alarm state to severity."""
    mapping = {
        'ALARM': 'HIGH',
        'INSUFFICIENT_DATA': 'MEDIUM',
        'OK': 'LOW'
    }
    return mapping.get(state, 'MEDIUM')


def generate_alert_id(alert: Dict[str, Any]) -> str:
    """Generate a unique but consistent ID for the alert."""
    # Create a signature from key fields
    signature_parts = [
        alert.get('source', ''),
        alert.get('source_id', ''),
        alert.get('title', ''),
        alert.get('timestamp', '')
    ]
    signature = '|'.join(str(p) for p in signature_parts)
    
    # Generate hash
    return hashlib.sha256(signature.encode()).hexdigest()[:16]

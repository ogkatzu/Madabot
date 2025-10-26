import json
import os
import boto3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from anthropic import Anthropic

dynamodb = boto3.resource('dynamodb')
logs_client = boto3.client('logs')
sqs = boto3.client('sqs')

ALERTS_TABLE = dynamodb.Table(os.environ['ALERTS_TABLE'])
CACHE_TABLE = dynamodb.Table(os.environ['ANALYSIS_CACHE_TABLE'])
DISTRIBUTION_QUEUE = os.environ['DISTRIBUTION_QUEUE_URL']
ANTHROPIC_API_KEY = os.environ['ANTHROPIC_API_KEY']

anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)


def analyze_alert(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for alert analysis using Claude AI.
    Processes alerts from SQS queue and generates intelligent reports.
    """
    for record in event['Records']:
        try:
            alert = json.loads(record['body'])
            
            # Check cache for similar alerts
            cached_analysis = check_analysis_cache(alert)
            if cached_analysis:
                print(f"Using cached analysis for alert {alert['alert_id']}")
                analysis = cached_analysis
            else:
                # Gather additional context
                context_data = gather_context(alert)
                
                # Perform AI analysis
                analysis = perform_claude_analysis(alert, context_data)
                
                # Cache the analysis
                cache_analysis(alert, analysis)
            
            # Store alert and analysis
            store_alert_data(alert, analysis)
            
            # Send to distribution
            send_to_distribution(alert, analysis)
            
        except Exception as e:
            print(f"Error analyzing alert: {str(e)}")
            raise


def gather_context(alert: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gather additional context for the alert from various sources.
    """
    context = {
        'recent_similar_alerts': get_recent_similar_alerts(alert),
        'log_context': get_log_context(alert),
        'historical_pattern': get_historical_pattern(alert)
    }
    
    return context


def get_recent_similar_alerts(alert: Dict[str, Any], hours: int = 24) -> list:
    """Fetch recent similar alerts from DynamoDB."""
    try:
        cutoff_time = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())
        
        response = ALERTS_TABLE.query(
            IndexName='timestamp-index',
            KeyConditionExpression='severity = :severity AND #ts > :cutoff',
            ExpressionAttributeNames={'#ts': 'timestamp'},
            ExpressionAttributeValues={
                ':severity': alert.get('severity', 'MEDIUM'),
                ':cutoff': cutoff_time
            },
            Limit=10
        )
        
        return response.get('Items', [])
    except Exception as e:
        print(f"Error fetching similar alerts: {str(e)}")
        return []


def get_log_context(alert: Dict[str, Any]) -> Optional[str]:
    """Fetch relevant log entries around the alert time."""
    if alert.get('source') != 'cloudwatch_logs':
        return None
    
    try:
        log_group = alert.get('log_group')
        log_stream = alert.get('log_stream')
        
        if not log_group or not log_stream:
            return None
        
        # Fetch logs around the alert time
        response = logs_client.get_log_events(
            logGroupName=log_group,
            logStreamName=log_stream,
            limit=50
        )
        
        events = response.get('events', [])
        return '\n'.join([e['message'] for e in events[-20:]])
        
    except Exception as e:
        print(f"Error fetching log context: {str(e)}")
        return None


def get_historical_pattern(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze historical patterns for this type of alert."""
    try:
        error_signature = generate_error_signature(alert)
        
        # Query past week for same error signature
        cutoff_time = int((datetime.utcnow() - timedelta(days=7)).timestamp())
        
        response = ALERTS_TABLE.scan(
            FilterExpression='error_signature = :sig AND #ts > :cutoff',
            ExpressionAttributeNames={'#ts': 'timestamp'},
            ExpressionAttributeValues={
                ':sig': error_signature,
                ':cutoff': cutoff_time
            }
        )
        
        items = response.get('Items', [])
        
        return {
            'occurrence_count': len(items),
            'first_seen': min([item['timestamp'] for item in items]) if items else None,
            'last_seen': max([item['timestamp'] for item in items]) if items else None,
            'frequency': calculate_frequency(items)
        }
        
    except Exception as e:
        print(f"Error analyzing historical pattern: {str(e)}")
        return {}


def calculate_frequency(items: list) -> str:
    """Calculate how frequently this error occurs."""
    if not items:
        return 'first_occurrence'
    
    if len(items) > 50:
        return 'very_frequent'
    elif len(items) > 10:
        return 'frequent'
    elif len(items) > 3:
        return 'occasional'
    else:
        return 'rare'


def perform_claude_analysis(alert: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use Claude AI to analyze the alert and generate an intelligent report.
    """
    prompt = build_analysis_prompt(alert, context)
    
    try:
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0,
            system=get_system_prompt(),
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        analysis_text = message.content[0].text
        
        # Parse Claude's structured response
        analysis = parse_claude_response(analysis_text)
        
        return analysis
        
    except Exception as e:
        print(f"Error in Claude analysis: {str(e)}")
        return generate_fallback_analysis(alert)


def get_system_prompt() -> str:
    """System prompt for Claude to act as an incident analyst."""
    return """You are an expert DevOps incident analyst. Your role is to analyze alerts and errors, 
provide clear assessments, and suggest actionable remediation steps.

For each alert, provide a structured analysis in JSON format with these fields:

{
  "summary": "Brief one-line summary of the issue",
  "severity_assessment": "CRITICAL|HIGH|MEDIUM|LOW with justification",
  "root_cause_hypothesis": "Most likely root cause based on the evidence",
  "affected_components": ["list", "of", "affected", "services"],
  "impact_assessment": "Description of business/technical impact",
  "remediation_steps": [
    "Step 1: Immediate action",
    "Step 2: Investigation steps",
    "Step 3: Resolution steps"
  ],
  "monitoring_recommendations": ["metrics", "to", "watch"],
  "related_documentation": ["relevant", "runbook", "links"],
  "confidence_level": "HIGH|MEDIUM|LOW",
  "requires_immediate_attention": true|false
}

Be concise, technical, and actionable. Focus on helping engineers quickly understand and resolve the issue."""


def build_analysis_prompt(alert: Dict[str, Any], context: Dict[str, Any]) -> str:
    """Build the analysis prompt for Claude."""
    prompt_parts = [
        "Analyze this production alert and provide a structured incident report:\n",
        f"Alert Source: {alert.get('source')}",
        f"Title: {alert.get('title')}",
        f"Severity: {alert.get('severity')}",
        f"Timestamp: {alert.get('timestamp')}",
        f"\nAlert Message:\n{alert.get('message')}\n"
    ]
    
    # Add log context if available
    if context.get('log_context'):
        prompt_parts.append(f"\nRecent Log Entries:\n{context['log_context'][:2000]}\n")
    
    # Add historical pattern
    if context.get('historical_pattern'):
        pattern = context['historical_pattern']
        prompt_parts.append(f"\nHistorical Pattern:")
        prompt_parts.append(f"- Occurrence Count (past 7 days): {pattern.get('occurrence_count', 0)}")
        prompt_parts.append(f"- Frequency: {pattern.get('frequency', 'unknown')}\n")
    
    # Add similar recent alerts
    if context.get('recent_similar_alerts'):
        prompt_parts.append(f"\nSimilar Alerts (past 24h): {len(context['recent_similar_alerts'])}\n")
    
    # Add raw data for complete context
    if alert.get('raw_data'):
        prompt_parts.append(f"\nRaw Alert Data:\n{json.dumps(alert['raw_data'], indent=2)[:1000]}\n")
    
    prompt_parts.append("\nProvide your analysis in the structured JSON format specified.")
    
    return '\n'.join(prompt_parts)


def parse_claude_response(response_text: str) -> Dict[str, Any]:
    """Parse Claude's JSON response."""
    try:
        # Extract JSON from response (Claude might wrap it in markdown)
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
        else:
            # If no JSON found, create structured output from text
            return {
                'summary': response_text[:200],
                'analysis_text': response_text,
                'requires_immediate_attention': 'critical' in response_text.lower()
            }
    except Exception as e:
        print(f"Error parsing Claude response: {str(e)}")
        return {'analysis_text': response_text}


def generate_fallback_analysis(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a basic analysis if Claude fails."""
    return {
        'summary': f"Alert: {alert.get('title')}",
        'severity_assessment': alert.get('severity', 'MEDIUM'),
        'impact_assessment': 'Automated analysis unavailable',
        'remediation_steps': [
            'Review alert details',
            'Check related logs and metrics',
            'Investigate affected service'
        ],
        'requires_immediate_attention': alert.get('severity') in ['CRITICAL', 'HIGH'],
        'confidence_level': 'LOW'
    }


def check_analysis_cache(alert: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Check if we have a recent analysis for this error signature."""
    try:
        error_signature = generate_error_signature(alert)
        
        response = CACHE_TABLE.get_item(
            Key={'error_signature': error_signature}
        )
        
        if 'Item' in response:
            cache_item = response['Item']
            # Check if cache is still valid (less than 1 hour old)
            cached_time = datetime.fromisoformat(cache_item['cached_at'])
            if datetime.utcnow() - cached_time < timedelta(hours=1):
                return cache_item['analysis']
        
        return None
        
    except Exception as e:
        print(f"Error checking cache: {str(e)}")
        return None


def cache_analysis(alert: Dict[str, Any], analysis: Dict[str, Any]):
    """Cache the analysis result."""
    try:
        error_signature = generate_error_signature(alert)
        ttl = int((datetime.utcnow() + timedelta(hours=24)).timestamp())
        
        CACHE_TABLE.put_item(
            Item={
                'error_signature': error_signature,
                'analysis': analysis,
                'cached_at': datetime.utcnow().isoformat(),
                'ttl': ttl
            }
        )
    except Exception as e:
        print(f"Error caching analysis: {str(e)}")


def generate_error_signature(alert: Dict[str, Any]) -> str:
    """Generate a signature for the error to enable caching and pattern matching."""
    # Use key characteristics to create signature
    signature_parts = [
        alert.get('source', ''),
        alert.get('title', ''),
        extract_error_type(alert.get('message', ''))
    ]
    
    signature = '|'.join(str(p) for p in signature_parts)
    return hashlib.sha256(signature.encode()).hexdigest()


def extract_error_type(message: str) -> str:
    """Extract the error type from message."""
    # Simple extraction - could be enhanced with regex patterns
    for line in message.split('\n'):
        if 'Exception' in line or 'Error' in line:
            return line.split(':')[0].strip()
    return ''


def store_alert_data(alert: Dict[str, Any], analysis: Dict[str, Any]):
    """Store alert and analysis in DynamoDB."""
    try:
        ALERTS_TABLE.put_item(
            Item={
                'alert_id': alert['alert_id'],
                'timestamp': int(datetime.fromisoformat(alert['timestamp'].replace('Z', '+00:00')).timestamp()),
                'severity': alert.get('severity', 'MEDIUM'),
                'source': alert.get('source'),
                'title': alert.get('title'),
                'message': alert.get('message'),
                'analysis': analysis,
                'error_signature': generate_error_signature(alert),
                'requires_immediate_attention': analysis.get('requires_immediate_attention', False),
                'created_at': datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        print(f"Error storing alert data: {str(e)}")
        raise


def send_to_distribution(alert: Dict[str, Any], analysis: Dict[str, Any]):
    """Send the analyzed alert to the distribution queue."""
    try:
        message_body = {
            'alert': alert,
            'analysis': analysis
        }
        
        sqs.send_message(
            QueueUrl=DISTRIBUTION_QUEUE,
            MessageBody=json.dumps(message_body),
            MessageAttributes={
                'severity': {
                    'StringValue': alert.get('severity', 'MEDIUM'),
                    'DataType': 'String'
                },
                'immediate_attention': {
                    'StringValue': str(analysis.get('requires_immediate_attention', False)),
                    'DataType': 'String'
                }
            }
        )
    except Exception as e:
        print(f"Error sending to distribution: {str(e)}")
        raise

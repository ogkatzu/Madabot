import json
import os
import boto3
from typing import Dict, Any, List
from datetime import datetime
import urllib3

http = urllib3.PoolManager()

SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')
JIRA_ENABLED = os.environ.get('JIRA_ENABLED', 'false').lower() == 'true'
EMAIL_ENABLED = os.environ.get('EMAIL_ENABLED', 'false').lower() == 'true'

ses = boto3.client('ses')
dynamodb = boto3.resource('dynamodb')
ALERTS_TABLE = dynamodb.Table(os.environ['ALERTS_TABLE'])


def distribute_report(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Distribute incident reports to configured channels.
    Currently supports: Slack, Jira (optional), Email (optional)
    """
    for record in event['Records']:
        try:
            message_data = json.loads(record['body'])
            alert = message_data['alert']
            analysis = message_data['analysis']
            
            # Send to all configured channels
            results = {}
            
            # Slack (always enabled in MVP)
            if SLACK_WEBHOOK_URL:
                results['slack'] = send_to_slack(alert, analysis)
            
            # Jira (optional)
            if JIRA_ENABLED:
                results['jira'] = send_to_jira(alert, analysis)
            
            # Email (optional)
            if EMAIL_ENABLED:
                results['email'] = send_to_email(alert, analysis)
            
            # Update alert record with distribution status
            update_distribution_status(alert['alert_id'], results)
            
            print(f"Distributed alert {alert['alert_id']}: {results}")
            
        except Exception as e:
            print(f"Error distributing report: {str(e)}")
            raise


def send_to_slack(alert: Dict[str, Any], analysis: Dict[str, Any]) -> bool:
    """Send formatted incident report to Slack."""
    try:
        slack_message = format_slack_message(alert, analysis)
        
        response = http.request(
            'POST',
            SLACK_WEBHOOK_URL,
            body=json.dumps(slack_message).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        return response.status == 200
        
    except Exception as e:
        print(f"Error sending to Slack: {str(e)}")
        return False


def format_slack_message(alert: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Format incident report for Slack with rich formatting."""
    
    severity = alert.get('severity', 'MEDIUM')
    severity_emoji = {
        'CRITICAL': ':rotating_light:',
        'HIGH': ':warning:',
        'MEDIUM': ':large_orange_diamond:',
        'LOW': ':information_source:'
    }.get(severity, ':question:')
    
    # Color coding
    color_map = {
        'CRITICAL': '#FF0000',
        'HIGH': '#FF6B00',
        'MEDIUM': '#FFD700',
        'LOW': '#36A64F'
    }
    
    # Build blocks for rich message
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{severity_emoji} {alert.get('title', 'Alert')}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Severity:*\n{severity}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Source:*\n{alert.get('source', 'Unknown')}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Time:*\n{format_timestamp(alert.get('timestamp'))}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Alert ID:*\n`{alert.get('alert_id', 'N/A')[:12]}`"
                }
            ]
        }
    ]
    
    # Add analysis summary
    if analysis.get('summary'):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Summary:*\n{analysis['summary']}"
            }
        })
    
    # Add root cause if available
    if analysis.get('root_cause_hypothesis'):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Probable Root Cause:*\n{analysis['root_cause_hypothesis']}"
            }
        })
    
    # Add impact assessment
    if analysis.get('impact_assessment'):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Impact:*\n{analysis['impact_assessment']}"
            }
        })
    
    # Add remediation steps
    if analysis.get('remediation_steps'):
        steps_text = '\n'.join([f"{i+1}. {step}" for i, step in enumerate(analysis['remediation_steps'])])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Remediation Steps:*\n{steps_text}"
            }
        })
    
    # Add affected components if available
    if analysis.get('affected_components'):
        components = ', '.join(analysis['affected_components'])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Affected Components:*\n{components}"
            }
        })
    
    # Add divider and actions
    blocks.append({"type": "divider"})
    
    # Action buttons
    actions = {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Acknowledge"
                },
                "style": "primary",
                "value": alert.get('alert_id')
            }
        ]
    }
    
    if analysis.get('requires_immediate_attention'):
        actions["elements"].append({
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "Escalate"
            },
            "style": "danger",
            "value": alert.get('alert_id')
        })
    
    blocks.append(actions)
    
    # Build final message
    message = {
        "blocks": blocks,
        "attachments": [
            {
                "color": color_map.get(severity, '#808080'),
                "blocks": blocks
            }
        ]
    }
    
    # Add immediate attention ping if critical
    if analysis.get('requires_immediate_attention'):
        message["text"] = f"<!channel> IMMEDIATE ATTENTION REQUIRED: {alert.get('title')}"
    else:
        message["text"] = f"Alert: {alert.get('title')}"
    
    return message


def send_to_jira(alert: Dict[str, Any], analysis: Dict[str, Any]) -> bool:
    """Create Jira ticket for the incident."""
    try:
        # This is a placeholder - implement Jira API integration
        jira_url = os.environ.get('JIRA_URL')
        jira_api_token = os.environ.get('JIRA_API_TOKEN')
        jira_project = os.environ.get('JIRA_PROJECT')
        
        if not all([jira_url, jira_api_token, jira_project]):
            print("Jira configuration incomplete")
            return False
        
        # Build Jira issue
        issue_data = {
            "fields": {
                "project": {"key": jira_project},
                "summary": alert.get('title'),
                "description": format_jira_description(alert, analysis),
                "issuetype": {"name": "Incident"},
                "priority": {"name": map_severity_to_jira_priority(alert.get('severity'))},
                "labels": [
                    "automated-alert",
                    f"severity-{alert.get('severity', 'medium').lower()}",
                    alert.get('source', 'unknown')
                ]
            }
        }
        
        # Add custom fields if needed
        if analysis.get('affected_components'):
            issue_data["fields"]["components"] = [
                {"name": comp} for comp in analysis['affected_components'][:5]
            ]
        
        # Make API call to create issue
        response = http.request(
            'POST',
            f"{jira_url}/rest/api/2/issue",
            body=json.dumps(issue_data).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {jira_api_token}'
            }
        )
        
        return response.status in [200, 201]
        
    except Exception as e:
        print(f"Error creating Jira ticket: {str(e)}")
        return False


def format_jira_description(alert: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    """Format incident description for Jira."""
    parts = [
        f"h2. Incident Summary",
        f"{analysis.get('summary', 'Automated alert triggered')}",
        "",
        f"h3. Alert Details",
        f"* *Source:* {alert.get('source')}",
        f"* *Severity:* {alert.get('severity')}",
        f"* *Timestamp:* {alert.get('timestamp')}",
        f"* *Alert ID:* {alert.get('alert_id')}",
        ""
    ]
    
    if analysis.get('root_cause_hypothesis'):
        parts.extend([
            "h3. Root Cause Hypothesis",
            analysis['root_cause_hypothesis'],
            ""
        ])
    
    if analysis.get('impact_assessment'):
        parts.extend([
            "h3. Impact Assessment",
            analysis['impact_assessment'],
            ""
        ])
    
    if analysis.get('remediation_steps'):
        parts.append("h3. Remediation Steps")
        for i, step in enumerate(analysis['remediation_steps'], 1):
            parts.append(f"# {step}")
        parts.append("")
    
    parts.extend([
        "h3. Alert Message",
        "{code}",
        alert.get('message', '')[:1000],
        "{code}"
    ])
    
    return '\n'.join(parts)


def map_severity_to_jira_priority(severity: str) -> str:
    """Map alert severity to Jira priority."""
    mapping = {
        'CRITICAL': 'Highest',
        'HIGH': 'High',
        'MEDIUM': 'Medium',
        'LOW': 'Low'
    }
    return mapping.get(severity, 'Medium')


def send_to_email(alert: Dict[str, Any], analysis: Dict[str, Any]) -> bool:
    """Send email notification for the incident."""
    try:
        email_to = os.environ.get('EMAIL_TO', '').split(',')
        email_from = os.environ.get('EMAIL_FROM')
        
        if not email_to or not email_from:
            print("Email configuration incomplete")
            return False
        
        subject = f"[{alert.get('severity')}] {alert.get('title')}"
        body_html = format_email_html(alert, analysis)
        body_text = format_email_text(alert, analysis)
        
        response = ses.send_email(
            Source=email_from,
            Destination={
                'ToAddresses': email_to
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Html': {
                        'Data': body_html,
                        'Charset': 'UTF-8'
                    },
                    'Text': {
                        'Data': body_text,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        
        return True
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False


def format_email_html(alert: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    """Format HTML email template."""
    severity_color = {
        'CRITICAL': '#DC3545',
        'HIGH': '#FD7E14',
        'MEDIUM': '#FFC107',
        'LOW': '#28A745'
    }.get(alert.get('severity'), '#6C757D')
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background-color: {severity_color}; color: white; padding: 20px; }}
            .content {{ padding: 20px; }}
            .section {{ margin-bottom: 20px; }}
            .label {{ font-weight: bold; }}
            .code {{ background-color: #f4f4f4; padding: 10px; border-left: 3px solid #007bff; }}
            ul {{ padding-left: 20px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{alert.get('title')}</h1>
            <p>Severity: {alert.get('severity')} | Source: {alert.get('source')}</p>
        </div>
        <div class="content">
            <div class="section">
                <span class="label">Summary:</span>
                <p>{analysis.get('summary', 'N/A')}</p>
            </div>
    """
    
    if analysis.get('root_cause_hypothesis'):
        html += f"""
            <div class="section">
                <span class="label">Root Cause Hypothesis:</span>
                <p>{analysis['root_cause_hypothesis']}</p>
            </div>
        """
    
    if analysis.get('impact_assessment'):
        html += f"""
            <div class="section">
                <span class="label">Impact Assessment:</span>
                <p>{analysis['impact_assessment']}</p>
            </div>
        """
    
    if analysis.get('remediation_steps'):
        steps_html = '<ol>' + ''.join([f'<li>{step}</li>' for step in analysis['remediation_steps']]) + '</ol>'
        html += f"""
            <div class="section">
                <span class="label">Remediation Steps:</span>
                {steps_html}
            </div>
        """
    
    html += f"""
            <div class="section">
                <span class="label">Alert Message:</span>
                <div class="code">{alert.get('message', '')[:500]}</div>
            </div>
            <div class="section">
                <p><small>Alert ID: {alert.get('alert_id')} | Time: {alert.get('timestamp')}</small></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def format_email_text(alert: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    """Format plain text email."""
    parts = [
        f"INCIDENT ALERT: {alert.get('title')}",
        f"Severity: {alert.get('severity')} | Source: {alert.get('source')}",
        "",
        f"Summary: {analysis.get('summary', 'N/A')}",
        ""
    ]
    
    if analysis.get('root_cause_hypothesis'):
        parts.extend([
            f"Root Cause: {analysis['root_cause_hypothesis']}",
            ""
        ])
    
    if analysis.get('remediation_steps'):
        parts.append("Remediation Steps:")
        for i, step in enumerate(analysis['remediation_steps'], 1):
            parts.append(f"{i}. {step}")
        parts.append("")
    
    parts.extend([
        f"Alert Message:",
        alert.get('message', '')[:500],
        "",
        f"Alert ID: {alert.get('alert_id')}",
        f"Timestamp: {alert.get('timestamp')}"
    ])
    
    return '\n'.join(parts)


def update_distribution_status(alert_id: str, results: Dict[str, bool]):
    """Update the alert record with distribution status."""
    try:
        ALERTS_TABLE.update_item(
            Key={'alert_id': alert_id},
            UpdateExpression='SET distribution_status = :status, distributed_at = :time',
            ExpressionAttributeValues={
                ':status': results,
                ':time': datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        print(f"Error updating distribution status: {str(e)}")


def format_timestamp(timestamp: str) -> str:
    """Format timestamp for display."""
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return timestamp

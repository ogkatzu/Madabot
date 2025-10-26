#!/usr/bin/env python3
"""
Generate architecture diagrams for the MCP Incident Response System.
Requires: diagrams library (pip install diagrams)
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.integration import SQS
from diagrams.aws.database import Dynamodb
from diagrams.aws.network import APIGateway
from diagrams.aws.management import Cloudwatch
from diagrams.aws.integration import SNS
from diagrams.custom import Custom
from diagrams.onprem.client import Users
from diagrams.onprem.chat import Slack
from diagrams.saas.chat import Teams


def generate_system_architecture():
    """Generate the main system architecture diagram."""
    
    with Diagram("MCP Incident Response System - High Level", 
                 filename="architecture_overview",
                 show=False,
                 direction="TB"):
        
        users = Users("Alert Sources")
        
        with Cluster("Ingestion Layer"):
            api = APIGateway("API Gateway")
            reception = Lambda("Alert Reception")
        
        with Cluster("Processing Layer"):
            processing_queue = SQS("Processing Queue")
            analysis = Lambda("AI Analysis\n(Claude)")
            
        with Cluster("Data Layer"):
            alerts_db = Dynamodb("Alerts Table")
            cache_db = Dynamodb("Analysis Cache")
        
        with Cluster("Distribution Layer"):
            dist_queue = SQS("Distribution Queue")
            distribution = Lambda("Distribution")
        
        with Cluster("Notification Channels"):
            slack = Slack("Slack")
            email = Users("Email")
        
        with Cluster("Monitoring"):
            cloudwatch = Cloudwatch("CloudWatch")
        
        # Flows
        users >> api >> reception >> processing_queue
        processing_queue >> analysis
        analysis >> Edge(label="store") >> alerts_db
        analysis >> Edge(label="cache") >> cache_db
        analysis >> dist_queue >> distribution
        distribution >> slack
        distribution >> email
        
        # Monitoring
        [reception, analysis, distribution] >> cloudwatch


def generate_detailed_flow():
    """Generate detailed message flow diagram."""
    
    with Diagram("Alert Processing Flow - Detailed",
                 filename="processing_flow",
                 show=False,
                 direction="LR"):
        
        with Cluster("Sources"):
            cw_alarm = Cloudwatch("CloudWatch\nAlarms")
            cw_logs = Cloudwatch("CloudWatch\nLogs")
            sns = SNS("SNS Topics")
        
        api = APIGateway("Webhook API")
        
        with Cluster("Reception Function"):
            normalize = Lambda("Normalize\nAlert")
            enrich = Lambda("Enrich\nMetadata")
        
        queue1 = SQS("Processing\nQueue")
        
        with Cluster("Analysis Function"):
            context = Lambda("Gather\nContext")
            cache_check = Lambda("Check\nCache")
            ai = Lambda("Claude\nAnalysis")
            store = Lambda("Store\nResults")
        
        queue2 = SQS("Distribution\nQueue")
        
        with Cluster("Distribution Function"):
            format_slack = Lambda("Format\nSlack")
            format_email = Lambda("Format\nEmail")
        
        slack = Slack("Slack")
        email = Users("Email")
        
        # Main flow
        [cw_alarm, cw_logs, sns] >> api
        api >> normalize >> enrich >> queue1
        queue1 >> context >> cache_check >> ai >> store >> queue2
        queue2 >> [format_slack, format_email]
        format_slack >> slack
        format_email >> email


def generate_data_model():
    """Generate data model diagram."""
    
    with Diagram("Data Model",
                 filename="data_model",
                 show=False,
                 direction="TB"):
        
        with Cluster("Alerts Table"):
            alerts = Dynamodb("Alerts\n\nPK: alert_id\nSK: timestamp\nGSI: severity-timestamp")
        
        with Cluster("Analysis Cache"):
            cache = Dynamodb("Cache\n\nPK: error_signature\nTTL: 24h")
        
        with Cluster("Operations"):
            write = Lambda("Write\nOperations")
            read = Lambda("Read\nOperations")
            query = Lambda("Query\nPatterns")
        
        write >> alerts
        read >> alerts
        query >> alerts
        
        write >> cache
        read >> cache


if __name__ == "__main__":
    print("Generating architecture diagrams...")
    
    try:
        generate_system_architecture()
        print("✓ Generated: architecture_overview.png")
    except Exception as e:
        print(f"✗ Error generating system architecture: {e}")
    
    try:
        generate_detailed_flow()
        print("✓ Generated: processing_flow.png")
    except Exception as e:
        print(f"✗ Error generating flow diagram: {e}")
    
    try:
        generate_data_model()
        print("✓ Generated: data_model.png")
    except Exception as e:
        print(f"✗ Error generating data model: {e}")
    
    print("\nDiagrams generated successfully!")
    print("Note: Install 'diagrams' package if not already installed:")
    print("  pip install diagrams")

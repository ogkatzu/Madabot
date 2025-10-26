#!/bin/bash

set -e

echo "Deploying MCP Incident Response System"

# Configuration
STACK_NAME="mcp-incident-responder"
ENVIRONMENT="dev"
S3_BUCKET=""
AWS_REGION="us-east-1"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --bucket)
      S3_BUCKET="$2"
      shift 2
      ;;
    --region)
      AWS_REGION="$2"
      shift 2
      ;;
    --slack-webhook)
      SLACK_WEBHOOK_URL="$2"
      shift 2
      ;;
    --anthropic-key)
      ANTHROPIC_API_KEY="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Validate required parameters
if [ -z "$S3_BUCKET" ]; then
  echo "Error: --bucket is required"
  echo "Usage: ./deploy.sh --bucket <s3-bucket> [options]"
  exit 1
fi

if [ -z "$SLACK_WEBHOOK_URL" ]; then
  echo "Warning: No Slack webhook URL provided. Please set it manually in AWS Console or use --slack-webhook"
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "Warning: No Anthropic API key provided. Please set it manually in AWS Console or use --anthropic-key"
fi

echo "Deployment Configuration:"
echo "  Environment: $ENVIRONMENT"
echo "  Region: $AWS_REGION"
echo "  S3 Bucket: $S3_BUCKET"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -t src/reception/ --quiet
pip install -r requirements.txt -t src/analysis/ --quiet
pip install -r requirements.txt -t src/distribution/ --quiet

# Build and package
echo "Building SAM application..."
sam build

echo "Packaging SAM application..."
sam package \
  --template-file .aws-sam/build/template.yaml \
  --s3-bucket "$S3_BUCKET" \
  --output-template-file packaged.yaml \
  --region "$AWS_REGION"

# Deploy
echo "Deploying CloudFormation stack..."
sam deploy \
  --template-file packaged.yaml \
  --stack-name "${STACK_NAME}-${ENVIRONMENT}" \
  --capabilities CAPABILITY_IAM \
  --region "$AWS_REGION" \
  --parameter-overrides \
    Environment="$ENVIRONMENT" \
    SlackWebhookUrl="${SLACK_WEBHOOK_URL:-placeholder}" \
    AnthropicApiKey="${ANTHROPIC_API_KEY:-placeholder}" \
  --no-fail-on-empty-changeset

# Get outputs
echo ""
echo "Deployment complete!"
echo ""
echo "Stack Outputs:"
aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}-${ENVIRONMENT}" \
  --region "$AWS_REGION" \
  --query 'Stacks[0].Outputs' \
  --output table

echo ""
echo "Next steps:"
echo "1. Note the WebhookUrl from the outputs above"
echo "2. Configure CloudWatch to send alerts to this webhook"
echo "3. If you didn't provide Slack/Anthropic credentials, update them in AWS Secrets Manager"
echo "4. Test the system by sending a sample alert"

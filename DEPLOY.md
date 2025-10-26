# Quick Deploy Guide

## 1. Setup Backend
```bash
make setup-backend ENV=dev
```

## 2. Set Secrets
```bash
export TF_VAR_google_api_key="YOUR_GEMINI_KEY"
export TF_VAR_slack_webhook_url="YOUR_SLACK_WEBHOOK"
export TF_VAR_owner_email="your@email.com"
```

## 3. Deploy
```bash
cd terraform
terraform init -backend-config=environments/dev-backend.tfvars
terraform apply -var-file=environments/dev.tfvars
```

## 4. Test
```bash
# Trigger test event
aws events put-events --entries '[{"Source":"test","DetailType":"test","Detail":"{}"}]'

# Check logs
make logs-analyzer
```

Done!

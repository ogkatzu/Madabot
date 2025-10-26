# Using Google Gemini API Instead of Claude

This guide shows you how to configure the MCP First-Responder to use Google's Gemini API instead of Anthropic's Claude API.

## Quick Configuration

### 1. Get Your Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy your API key

### 2. Update Configuration

Edit `terraform/environments/dev.tfvars`:

```hcl
# AI Provider Configuration
ai_provider = "google"  # Changed from "anthropic" to "google"
```

### 3. Set Environment Variable

```bash
# Instead of:
# export TF_VAR_anthropic_api_key="sk-ant-api03-..."

# Use:
export TF_VAR_google_api_key="YOUR_GOOGLE_API_KEY"
export TF_VAR_slack_webhook_url="https://hooks.slack.com/services/..."
export TF_VAR_owner_email="your-email@example.com"
```

### 4. Deploy

```bash
cd terraform
terraform init -backend-config=environments/dev-backend.tfvars
terraform apply -var-file=environments/dev.tfvars
```

Or using the Makefile:

```bash
make deploy ENV=dev
```

## Configuration Details

### Terraform Variables

The infrastructure automatically configures based on `ai_provider`:

| Variable | Description | When Using Gemini |
|----------|-------------|-------------------|
| `ai_provider` | AI provider choice | Set to `"google"` |
| `google_api_key` | Gemini API key | **Required** |
| `anthropic_api_key` | Claude API key | Not used (can be empty) |

### Lambda Environment Variables

When `ai_provider = "google"`, the analyzer Lambda receives:

```bash
AI_PROVIDER=google
GOOGLE_API_KEY_PARAM=/mcp-first-responder/dev/google-api-key
```

When `ai_provider = "anthropic"`, it receives:

```bash
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY_PARAM=/mcp-first-responder/dev/anthropic-api-key
```

## Lambda Code Implementation

Your analyzer Lambda (`lambdas/analyzer/handler.py`) should check the `AI_PROVIDER` environment variable:

```python
import os
import boto3

def lambda_handler(event, context):
    ai_provider = os.environ.get('AI_PROVIDER', 'anthropic')

    if ai_provider == 'google':
        # Use Google Gemini
        api_key_param = os.environ['GOOGLE_API_KEY_PARAM']
        api_key = get_ssm_parameter(api_key_param)
        response = call_gemini_api(api_key, prompt)
    else:
        # Use Anthropic Claude
        api_key_param = os.environ['ANTHROPIC_API_KEY_PARAM']
        api_key = get_ssm_parameter(api_key_param)
        response = call_claude_api(api_key, prompt)

    return response

def get_ssm_parameter(param_name):
    ssm = boto3.client('ssm')
    response = ssm.get_parameter(Name=param_name, WithDecryption=True)
    return response['Parameter']['Value']

def call_gemini_api(api_key, prompt):
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-pro')

    response = model.generate_content(prompt)
    return response.text

def call_claude_api(api_key, prompt):
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text
```

## Cost Comparison

### Google Gemini Pricing (as of 2024)

**Gemini 1.5 Pro**:
- Input: $0.00125 per 1K tokens
- Output: $0.005 per 1K tokens
- **~$0.015 per analysis** (assuming 10K input tokens, 2K output)

**Gemini 1.5 Flash** (faster, cheaper):
- Input: $0.000075 per 1K tokens
- Output: $0.0003 per 1K tokens
- **~$0.0015 per analysis** (10x cheaper!)

### Anthropic Claude Pricing

**Claude 3.5 Sonnet**:
- Input: $0.003 per 1K tokens
- Output: $0.015 per 1K tokens
- **~$0.045 per analysis** (assuming 10K input, 2K output)

### Monthly Cost Comparison (3,000 alerts/month)

| Service | Claude 3.5 | Gemini 1.5 Pro | Gemini 1.5 Flash |
|---------|------------|----------------|------------------|
| AI API  | $135       | $45            | $4.50            |
| Other AWS | $13      | $13            | $13              |
| **Total** | **$148** | **$58**        | **$17.50**       |

**Savings with Gemini Flash**: ~88% reduction in AI costs!

## Gemini API Models

### Recommended Models

1. **gemini-1.5-pro** (Recommended for quality)
   - Best for complex analysis
   - Similar quality to Claude 3.5 Sonnet
   - 3x cheaper than Claude
   - 2M token context window

2. **gemini-1.5-flash** (Recommended for cost)
   - Fast and efficient
   - Great for structured tasks
   - 10x cheaper than Claude
   - 1M token context window

### Model Selection in Lambda

```python
# For high-quality analysis
model = genai.GenerativeModel('gemini-1.5-pro')

# For cost-effective analysis
model = genai.GenerativeModel('gemini-1.5-flash')

# With system instructions
model = genai.GenerativeModel(
    'gemini-1.5-pro',
    system_instruction="You are an expert DevOps engineer analyzing incident alerts..."
)
```

## Lambda Dependencies

Update `lambdas/analyzer/requirements.txt`:

```txt
# For Google Gemini
google-generativeai==0.3.2
google-ai-generativelanguage==0.4.0

# For Anthropic Claude (if keeping both options)
anthropic==0.39.0

# AWS SDK
boto3==1.35.0
```

## Switching Providers

To switch from Gemini back to Claude (or vice versa):

1. Update `terraform/environments/dev.tfvars`:
   ```hcl
   ai_provider = "anthropic"  # or "google"
   ```

2. Set the appropriate API key:
   ```bash
   export TF_VAR_anthropic_api_key="..."  # for Claude
   # or
   export TF_VAR_google_api_key="..."     # for Gemini
   ```

3. Apply changes:
   ```bash
   terraform apply -var-file=environments/dev.tfvars
   ```

The Lambda code will automatically use the correct provider based on the `AI_PROVIDER` environment variable.

## Testing Gemini Integration

1. Deploy with Gemini configuration
2. Trigger a test alert:
   ```bash
   make test-ingestor
   ```

3. Check analyzer logs:
   ```bash
   make logs-analyzer
   ```

4. Verify the AI provider in outputs:
   ```bash
   terraform output ai_provider
   # Should show: google
   ```

## Troubleshooting

### API Key Not Working

```bash
# Verify parameter exists in SSM
aws ssm get-parameter \
  --name /mcp-first-responder/dev/google-api-key \
  --with-decryption

# Check Lambda has permission
aws iam get-role-policy \
  --role-name mcp-first-responder-dev-analyzer-role \
  --policy-name analyzer-permissions
```

### Gemini API Errors

Common errors:
- **403 Forbidden**: API key invalid or not activated
- **429 Too Many Requests**: Rate limit exceeded (use caching!)
- **400 Bad Request**: Invalid model name or prompt format

Check logs:
```bash
aws logs tail /aws/lambda/mcp-first-responder-dev-analyzer --follow
```

## Best Practices

1. **Use Gemini 1.5 Flash** for cost optimization
2. **Implement caching** (already included in architecture)
3. **Set retry logic** for rate limits
4. **Monitor token usage** via CloudWatch

## Additional Resources

- [Google AI Studio](https://makersuite.google.com/)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [Gemini Pricing](https://ai.google.dev/pricing)
- [Python Client Library](https://github.com/google/generative-ai-python)

## Support

For Gemini-specific issues:
- Check [Google AI Forum](https://discuss.ai.google.dev/)
- Review [Gemini API Cookbook](https://github.com/google-gemini/cookbook)

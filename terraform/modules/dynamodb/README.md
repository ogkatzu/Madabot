# DynamoDB Module

This module creates DynamoDB tables with support for GSIs, LSIs, TTL, streams, and encryption.

## Features

- Support for both PAY_PER_REQUEST and PROVISIONED billing modes
- Global and Local Secondary Indexes
- TTL for automatic item expiration
- DynamoDB Streams
- Server-side encryption with KMS or AWS managed keys
- Point-in-time recovery
- Flexible attribute definitions

## Usage

### Simple Table

```hcl
module "simple_table" {
  source = "./modules/dynamodb"

  table_name   = "my-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"
  hash_key_type = "S"

  attributes = [
    {
      name = "id"
      type = "S"
    }
  ]

  tags = {
    Environment = "dev"
  }
}
```

### Table with GSI and TTL

```hcl
module "complex_table" {
  source = "./modules/dynamodb"

  table_name   = "alerts-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "alert_id"
  hash_key_type = "S"

  attributes = [
    {
      name = "alert_id"
      type = "S"
    },
    {
      name = "severity"
      type = "S"
    },
    {
      name = "timestamp"
      type = "N"
    }
  ]

  global_secondary_indexes = [
    {
      name            = "severity-timestamp-index"
      hash_key        = "severity"
      range_key       = "timestamp"
      projection_type = "ALL"
    }
  ]

  enable_ttl = true
  ttl_attribute_name = "expires_at"

  enable_streams = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  tags = {
    Environment = "dev"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| table_name | Name of the DynamoDB table | string | n/a | yes |
| billing_mode | Billing mode (PAY_PER_REQUEST or PROVISIONED) | string | "PAY_PER_REQUEST" | no |
| hash_key | Hash key (partition key) | string | n/a | yes |
| hash_key_type | Type of hash key (S, N, B) | string | "S" | no |
| range_key | Range key (sort key) | string | null | no |
| attributes | List of attribute definitions | list(object) | n/a | yes |
| global_secondary_indexes | List of GSIs | list(object) | [] | no |
| enable_ttl | Enable TTL | bool | false | no |
| enable_streams | Enable DynamoDB streams | bool | false | no |
| enable_encryption | Enable server-side encryption | bool | true | no |

## Outputs

| Name | Description |
|------|-------------|
| table_name | Name of the table |
| table_arn | ARN of the table |
| stream_arn | ARN of the stream (if enabled) |
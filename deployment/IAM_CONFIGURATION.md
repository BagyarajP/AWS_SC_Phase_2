# IAM Configuration for Supply Chain AI Platform

## Overview

This document describes the IAM roles and policies required for the Supply Chain AI Platform components.

## IAM Roles

### 1. SupplyChainBedrockAgentRole

**Purpose**: Allows Bedrock Agents to invoke Lambda tools and use foundation models

**Trust Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "YOUR_ACCOUNT_ID"
        }
      }
    }
  ]
}
```

**Permissions Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:forecasting-*",
        "arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:procurement-*",
        "arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:inventory-*"
      ]
    }
  ]
}
```

### 2. SupplyChainToolRole

**Purpose**: Allows Lambda tools to access Redshift Data API and CloudWatch

**Trust Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Permissions Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "redshift-data:ExecuteStatement",
        "redshift-data:GetStatementResult",
        "redshift-data:DescribeStatement",
        "redshift-data:CancelStatement"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "redshift-serverless:GetWorkgroup",
        "redshift-serverless:GetNamespace"
      ],
      "Resource": [
        "arn:aws:redshift-serverless:us-east-1:YOUR_ACCOUNT_ID:workgroup/*",
        "arn:aws:redshift-serverless:us-east-1:YOUR_ACCOUNT_ID:namespace/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:YOUR_ACCOUNT_ID:log-group:/aws/lambda/*"
    }
  ]
}
```

### 3. SupplyChainGlueRole

**Purpose**: Allows Glue job to access S3 and Redshift Serverless

**Trust Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "glue.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Permissions Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::supply-chain-data-*",
        "arn:aws:s3:::supply-chain-data-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "redshift-data:ExecuteStatement",
        "redshift-data:GetStatementResult",
        "redshift-data:DescribeStatement"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:YOUR_ACCOUNT_ID:log-group:/aws-glue/*"
    }
  ]
}
```

### 4. SupplyChainStreamlitRole

**Purpose**: Allows Streamlit app on SageMaker to access Redshift, Bedrock, and Lambda

**Trust Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "sagemaker.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Permissions Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent",
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1:YOUR_ACCOUNT_ID:agent/*",
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "redshift-data:ExecuteStatement",
        "redshift-data:GetStatementResult",
        "redshift-data:DescribeStatement"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:*"
      ]
    }
  ]
}
```

## Deployment

### Create All Roles

```bash
# Set your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create Bedrock Agent Role
aws iam create-role \
  --role-name SupplyChainBedrockAgentRole \
  --assume-role-policy-document file://trust-policies/bedrock-agent-trust.json

aws iam put-role-policy \
  --role-name SupplyChainBedrockAgentRole \
  --policy-name BedrockAgentPermissions \
  --policy-document file://policies/bedrock-agent-policy.json

# Create Lambda Tool Role
aws iam create-role \
  --role-name SupplyChainToolRole \
  --assume-role-policy-document file://trust-policies/lambda-trust.json

aws iam put-role-policy \
  --role-name SupplyChainToolRole \
  --policy-name LambdaToolPermissions \
  --policy-document file://policies/lambda-tool-policy.json

# Create Glue Role
aws iam create-role \
  --role-name SupplyChainGlueRole \
  --assume-role-policy-document file://trust-policies/glue-trust.json

aws iam put-role-policy \
  --role-name SupplyChainGlueRole \
  --policy-name GlueJobPermissions \
  --policy-document file://policies/glue-policy.json

# Create SageMaker Role
aws iam create-role \
  --role-name SupplyChainStreamlitRole \
  --assume-role-policy-document file://trust-policies/sagemaker-trust.json

aws iam put-role-policy \
  --role-name SupplyChainStreamlitRole \
  --policy-name StreamlitPermissions \
  --policy-document file://policies/sagemaker-policy.json
```

## Authentication Logging

All authentication attempts and Bedrock Agent invocations are logged to CloudWatch:

- **Log Group**: `/aws/bedrock/agents/supply-chain-*`
- **Metrics**: Authentication success/failure rates
- **Retention**: 30 days

## Security Best Practices

1. **Least Privilege**: Each role has only the permissions needed
2. **Resource Restrictions**: Policies use specific resource ARNs where possible
3. **Condition Keys**: Trust policies use condition keys to restrict access
4. **Regular Audits**: Review IAM policies quarterly
5. **CloudWatch Monitoring**: Monitor all authentication attempts

## Requirements Validated

- **9.4**: IAM roles configured for all components
- **9.7**: Authentication logging enabled

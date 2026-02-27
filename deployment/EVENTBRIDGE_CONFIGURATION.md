# EventBridge Configuration for Supply Chain AI Platform

## Overview

EventBridge schedules trigger Bedrock Agents daily for autonomous supply chain operations.

## Schedules

### 1. Forecasting Agent Schedule

**Schedule**: Daily at 1:00 AM UTC  
**Target**: Forecasting Bedrock Agent  
**Purpose**: Generate demand forecasts for all SKUs

**EventBridge Rule**:
```json
{
  "Name": "supply-chain-forecasting-daily",
  "Description": "Trigger Forecasting Bedrock Agent daily at 1:00 AM UTC",
  "ScheduleExpression": "cron(0 1 * * ? *)",
  "State": "ENABLED",
  "Targets": [
    {
      "Id": "1",
      "Arn": "arn:aws:bedrock:us-east-1:YOUR_ACCOUNT_ID:agent/FORECASTING_AGENT_ID",
      "RoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/EventBridgeBedrockAgentRole",
      "Input": "{\"inputText\": \"Generate 7-day and 30-day forecasts for all products. Calculate accuracy for previous forecasts.\"}"
    }
  ]
}
```

### 2. Procurement Agent Schedule

**Schedule**: Daily at 2:00 AM UTC  
**Target**: Procurement Bedrock Agent  
**Purpose**: Check inventory and create purchase orders

**EventBridge Rule**:
```json
{
  "Name": "supply-chain-procurement-daily",
  "Description": "Trigger Procurement Bedrock Agent daily at 2:00 AM UTC",
  "ScheduleExpression": "cron(0 2 * * ? *)",
  "State": "ENABLED",
  "Targets": [
    {
      "Id": "1",
      "Arn": "arn:aws:bedrock:us-east-1:YOUR_ACCOUNT_ID:agent/PROCUREMENT_AGENT_ID",
      "RoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/EventBridgeBedrockAgentRole",
      "Input": "{\"inputText\": \"Check inventory levels for all products. Create purchase orders for items below reorder point.\"}"
    }
  ]
}
```

### 3. Inventory Agent Schedule

**Schedule**: Daily at 3:00 AM UTC  
**Target**: Inventory Bedrock Agent  
**Purpose**: Analyze inventory imbalances and recommend transfers

**EventBridge Rule**:
```json
{
  "Name": "supply-chain-inventory-daily",
  "Description": "Trigger Inventory Bedrock Agent daily at 3:00 AM UTC",
  "ScheduleExpression": "cron(0 3 * * ? *)",
  "State": "ENABLED",
  "Targets": [
    {
      "Id": "1",
      "Arn": "arn:aws:bedrock:us-east-1:YOUR_ACCOUNT_ID:agent/INVENTORY_AGENT_ID",
      "RoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/EventBridgeBedrockAgentRole",
      "Input": "{\"inputText\": \"Analyze inventory across all warehouses. Recommend transfers to balance inventory based on demand forecasts.\"}"
    }
  ]
}
```

## IAM Role for EventBridge

**Role Name**: `EventBridgeBedrockAgentRole`

**Trust Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "events.amazonaws.com"
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
        "bedrock:InvokeAgent"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1:YOUR_ACCOUNT_ID:agent/*"
      ]
    }
  ]
}
```

## Deployment

### Create EventBridge Rules

```bash
# Set variables
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
FORECASTING_AGENT_ID="your-forecasting-agent-id"
PROCUREMENT_AGENT_ID="your-procurement-agent-id"
INVENTORY_AGENT_ID="your-inventory-agent-id"

# Create IAM role for EventBridge
aws iam create-role \
  --role-name EventBridgeBedrockAgentRole \
  --assume-role-policy-document file://eventbridge-trust-policy.json

aws iam put-role-policy \
  --role-name EventBridgeBedrockAgentRole \
  --policy-name InvokeBedrockAgent \
  --policy-document file://eventbridge-policy.json

# Create Forecasting Agent schedule
aws events put-rule \
  --name supply-chain-forecasting-daily \
  --schedule-expression "cron(0 1 * * ? *)" \
  --state ENABLED \
  --description "Trigger Forecasting Bedrock Agent daily at 1:00 AM UTC"

aws events put-targets \
  --rule supply-chain-forecasting-daily \
  --targets file://forecasting-target.json

# Create Procurement Agent schedule
aws events put-rule \
  --name supply-chain-procurement-daily \
  --schedule-expression "cron(0 2 * * ? *)" \
  --state ENABLED \
  --description "Trigger Procurement Bedrock Agent daily at 2:00 AM UTC"

aws events put-targets \
  --rule supply-chain-procurement-daily \
  --targets file://procurement-target.json

# Create Inventory Agent schedule
aws events put-rule \
  --name supply-chain-inventory-daily \
  --schedule-expression "cron(0 3 * * ? *)" \
  --state ENABLED \
  --description "Trigger Inventory Bedrock Agent daily at 3:00 AM UTC"

aws events put-targets \
  --rule supply-chain-inventory-daily \
  --targets file://inventory-target.json
```

## Monitoring

### CloudWatch Metrics

- **Invocations**: Number of agent invocations
- **Failures**: Failed invocations
- **Duration**: Agent execution time

### CloudWatch Alarms

```bash
# Create alarm for failed invocations
aws cloudwatch put-metric-alarm \
  --alarm-name supply-chain-agent-failures \
  --alarm-description "Alert on Bedrock Agent failures" \
  --metric-name FailedInvocations \
  --namespace AWS/Events \
  --statistic Sum \
  --period 3600 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold
```

## Testing

### Manual Trigger

```bash
# Manually trigger a rule for testing
aws events put-events \
  --entries '[{
    "Source": "manual.test",
    "DetailType": "Test Event",
    "Detail": "{\"test\": true}"
  }]'
```

### Verify Execution

```bash
# Check CloudWatch Logs
aws logs tail /aws/bedrock/agents/supply-chain-forecasting-agent --follow
```

## Requirements Validated

- **3.7**: Forecasting agent scheduled daily
- **8.1**: Procurement agent scheduled daily
- **8.2**: Inventory agent scheduled daily
- **8.3**: EventBridge configuration in us-east-1

## Cost Estimation

- **EventBridge Rules**: $1.00 per million events
- **3 rules × 1 invocation/day × 30 days**: 90 events/month
- **Monthly Cost**: < $0.01 (effectively free)

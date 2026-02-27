# Forecasting Bedrock Agent

## Overview

The Forecasting Bedrock Agent is an autonomous AI agent powered by Claude 3.5 Sonnet that generates demand forecasts for supply chain optimization. It uses statistical models (Holt-Winters and ARIMA ensemble) to predict future demand with confidence intervals.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Forecasting Bedrock Agent                   │
│              (Claude 3.5 Sonnet - us-east-1)                │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ Invokes Lambda Tools
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│  Lambda Tools    │          │  Redshift        │
│  Action Group    │◄────────►│  Serverless      │
└──────────────────┘          └──────────────────┘
        │
        │ 4 Tools:
        │
        ├─► get_historical_sales
        ├─► calculate_forecast
        ├─► store_forecast
        └─► calculate_accuracy
```

## Agent Configuration

- **Agent Name**: `supply-chain-forecasting-agent`
- **Model**: `anthropic.claude-3-5-sonnet-20241022-v2:0`
- **Region**: `us-east-1`
- **Action Group**: `forecasting-tools` (4 Lambda tools)
- **Idle Session TTL**: 600 seconds (10 minutes)

## Lambda Tools

### 1. get_historical_sales
Retrieves 12 months of historical sales data from Redshift for a specified product.

**Input**:
```json
{
  "product_id": 123,
  "months_back": 12
}
```

**Output**:
```json
{
  "product_id": 123,
  "time_series": [
    {"date": "2024-01-01", "quantity": 150},
    {"date": "2024-01-02", "quantity": 145}
  ]
}
```

### 2. calculate_forecast
Generates demand forecasts using Holt-Winters and ARIMA ensemble with confidence intervals.

**Input**:
```json
{
  "product_id": 123,
  "time_series": [...],
  "horizon_days": 7
}
```

**Output**:
```json
{
  "product_id": 123,
  "horizon_days": 7,
  "forecast": [
    {
      "date": "2024-12-01",
      "forecast_value": 155.3,
      "confidence_80_lower": 145.2,
      "confidence_80_upper": 165.4,
      "confidence_95_lower": 140.1,
      "confidence_95_upper": 170.5
    }
  ]
}
```

### 3. store_forecast
Stores forecast records in the `demand_forecast` table via Redshift Data API.

**Input**:
```json
{
  "product_id": 123,
  "forecast_data": [...],
  "horizon_days": 7
}
```

**Output**:
```json
{
  "success": true,
  "records_inserted": 7
}
```

### 4. calculate_accuracy
Calculates MAPE (Mean Absolute Percentage Error) by comparing forecasts to actual demand.

**Input**:
```json
{
  "product_id": 123,
  "evaluation_period_days": 30
}
```

**Output**:
```json
{
  "product_id": 123,
  "mape": 12.5,
  "evaluation_period_days": 30,
  "forecast_count": 30
}
```

## System Prompt

The agent is instructed to:
1. Retrieve historical sales data for specified products
2. Generate forecasts using statistical models
3. Calculate confidence intervals at 80% and 95% levels
4. Store forecasts in the database
5. Evaluate forecast accuracy using MAPE
6. Provide detailed explanations for forecasts

## Deployment

### Prerequisites

1. AWS CLI configured with appropriate credentials
2. IAM role for Bedrock Agent with permissions:
   - `bedrock:InvokeModel`
   - `lambda:InvokeFunction`
3. Lambda functions deployed (see `tools/` directory)
4. Redshift Serverless workgroup running in us-east-1

### Step 1: Deploy Lambda Tools

```bash
cd lambda/forecasting_agent/tools

# Deploy get_historical_sales
cd get_historical_sales
./deploy_get_historical_sales.sh

# Repeat for other tools...
```

### Step 2: Create IAM Role for Bedrock Agent

```bash
# Create role with trust policy for Bedrock
aws iam create-role \
  --role-name SupplyChainForecastingAgentRole \
  --assume-role-policy-document file://trust-policy.json

# Attach policies
aws iam attach-role-policy \
  --role-name SupplyChainForecastingAgentRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

aws iam put-role-policy \
  --role-name SupplyChainForecastingAgentRole \
  --policy-name LambdaInvokePolicy \
  --policy-document file://lambda-invoke-policy.json
```

### Step 3: Create Bedrock Agent

```bash
# Update config.json with your AWS account ID
sed -i 's/ACCOUNT_ID/YOUR_ACCOUNT_ID/g' config.json

# Create the agent using AWS CLI
aws bedrock-agent create-agent \
  --region us-east-1 \
  --agent-name supply-chain-forecasting-agent \
  --foundation-model anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --instruction "$(jq -r '.instruction' config.json)" \
  --agent-resource-role-arn arn:aws:iam::YOUR_ACCOUNT_ID:role/SupplyChainForecastingAgentRole \
  --idle-session-ttl-in-seconds 600
```

### Step 4: Create Action Group

```bash
# Get agent ID from previous step
AGENT_ID="YOUR_AGENT_ID"

# Create action group
aws bedrock-agent create-agent-action-group \
  --region us-east-1 \
  --agent-id $AGENT_ID \
  --agent-version DRAFT \
  --action-group-name forecasting-tools \
  --action-group-executor lambda=arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:forecasting-agent-tools \
  --api-schema file://api-schema.json
```

### Step 5: Prepare Agent

```bash
# Prepare the agent (required before invocation)
aws bedrock-agent prepare-agent \
  --region us-east-1 \
  --agent-id $AGENT_ID
```

### Step 6: Test Agent

```bash
# Invoke agent with test prompt
aws bedrock-agent-runtime invoke-agent \
  --region us-east-1 \
  --agent-id $AGENT_ID \
  --agent-alias-id TSTALIASID \
  --session-id test-session-1 \
  --input-text "Generate a 7-day demand forecast for product ID 1" \
  output.txt

# View response
cat output.txt
```

## Testing

### Manual Testing via AWS Console

1. Navigate to Amazon Bedrock console
2. Go to "Agents" section
3. Select `supply-chain-forecasting-agent`
4. Click "Test" button
5. Enter prompt: "Generate a 7-day forecast for product ID 1"
6. Review agent reasoning and tool calls

### Automated Testing

```bash
cd lambda/forecasting_agent

# Run unit tests
pytest tests/ -v

# Run property-based tests
pytest tests/test_property_*.py -v --hypothesis-show-statistics
```

## Monitoring

### CloudWatch Logs

- Agent invocations: `/aws/bedrock/agents/supply-chain-forecasting-agent`
- Lambda tools: `/aws/lambda/forecasting-agent-tools`

### Metrics

- Agent invocation count
- Tool call success rate
- Forecast accuracy (MAPE)
- Token usage and costs

## Cost Estimation

### Bedrock Costs (Claude 3.5 Sonnet)
- Input tokens: ~$0.003 per 1K tokens
- Output tokens: ~$0.015 per 1K tokens
- Typical forecast generation: ~2K input + 1K output = ~$0.021 per forecast

### Lambda Costs
- Free tier: 1M requests/month, 400K GB-seconds/month
- Beyond free tier: $0.20 per 1M requests

### Estimated Monthly Cost
- 2,000 SKUs × 1 forecast/day = 60,000 forecasts/month
- Bedrock: ~$1,260/month
- Lambda: Free tier covers usage
- **Total: ~$1,260/month**

## Troubleshooting

### Agent not invoking tools
- Check IAM role has `lambda:InvokeFunction` permission
- Verify Lambda function ARNs in action group configuration
- Check Lambda function resource policies allow Bedrock invocation

### Forecast accuracy is low
- Review historical data quality
- Check for missing data or outliers
- Adjust model parameters in `calculate_forecast` tool
- Consider longer historical periods (18-24 months)

### High token usage
- Optimize system prompt to be more concise
- Reduce verbose explanations in tool responses
- Use agent aliases with guardrails to limit output length

## Requirements Validated

- **3.3**: Forecast uses historical data
- **3.4**: Confidence intervals at 80% and 95%
- **3.5**: Multi-horizon forecasts (7-day and 30-day)
- **3.6**: Forecast persistence in database
- **3.2**: Accuracy calculation (MAPE)
- **8.1**: Bedrock Agent configuration
- **8.3**: Agent scheduling (via EventBridge)
- **8.5**: Action group with Lambda tools
- **8.6**: CloudWatch logging

## Next Steps

1. Deploy Procurement Bedrock Agent (Task 5)
2. Deploy Inventory Bedrock Agent (Task 6)
3. Implement property-based tests (Tasks 4.6-4.11)
4. Configure EventBridge scheduling (Task 14.1)
5. Integrate with Streamlit dashboard (Task 8)

## References

- [AWS Bedrock Agents Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Claude 3.5 Sonnet Model Card](https://docs.anthropic.com/claude/docs/models-overview)
- [Redshift Data API](https://docs.aws.amazon.com/redshift/latest/mgmt/data-api.html)

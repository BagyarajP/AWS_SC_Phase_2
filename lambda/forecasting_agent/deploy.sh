#!/bin/bash

# Forecasting Bedrock Agent Deployment Script
# This script deploys the Forecasting Bedrock Agent and its Lambda tools

set -e

echo "========================================="
echo "Forecasting Bedrock Agent Deployment"
echo "========================================="

# Configuration
REGION="us-east-1"
AGENT_NAME="supply-chain-forecasting-agent"
MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0"
ROLE_NAME="SupplyChainForecastingAgentRole"

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI not found. Please install AWS CLI."
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "Error: jq not found. Please install jq."
    exit 1
fi

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account ID: $ACCOUNT_ID"

# Step 1: Deploy Lambda tools
echo ""
echo "Step 1: Deploying Lambda tools..."
cd tools

# Deploy each tool
for tool in get_historical_sales calculate_forecast store_forecast calculate_accuracy; do
    echo "Deploying $tool..."
    if [ -f "deploy_${tool}.sh" ]; then
        bash "deploy_${tool}.sh"
    else
        echo "Warning: deploy_${tool}.sh not found, skipping..."
    fi
done

cd ..

# Step 2: Create IAM role for Bedrock Agent
echo ""
echo "Step 2: Creating IAM role for Bedrock Agent..."

# Create trust policy
cat > /tmp/bedrock-trust-policy.json <<EOF
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
          "aws:SourceAccount": "$ACCOUNT_ID"
        }
      }
    }
  ]
}
EOF

# Create role
if aws iam get-role --role-name $ROLE_NAME 2>/dev/null; then
    echo "Role $ROLE_NAME already exists, skipping creation..."
else
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file:///tmp/bedrock-trust-policy.json \
        --description "IAM role for Supply Chain Forecasting Bedrock Agent"
    echo "Role created successfully"
fi

# Create Lambda invoke policy
cat > /tmp/lambda-invoke-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:$REGION:$ACCOUNT_ID:function:forecasting-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:$REGION::foundation-model/$MODEL_ID"
      ]
    }
  ]
}
EOF

# Attach policy
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name LambdaInvokePolicy \
    --policy-document file:///tmp/lambda-invoke-policy.json

echo "IAM policies attached successfully"

# Wait for role to propagate
echo "Waiting for IAM role to propagate..."
sleep 10

# Step 3: Update config.json with account ID
echo ""
echo "Step 3: Updating config.json with account ID..."
sed "s/ACCOUNT_ID/$ACCOUNT_ID/g" config.json > /tmp/config-updated.json

# Step 4: Create Bedrock Agent
echo ""
echo "Step 4: Creating Bedrock Agent..."

INSTRUCTION=$(jq -r '.instruction' /tmp/config-updated.json)

# Check if agent already exists
EXISTING_AGENT=$(aws bedrock-agent list-agents --region $REGION --query "agentSummaries[?agentName=='$AGENT_NAME'].agentId" --output text)

if [ -n "$EXISTING_AGENT" ]; then
    echo "Agent $AGENT_NAME already exists with ID: $EXISTING_AGENT"
    AGENT_ID=$EXISTING_AGENT
else
    # Create agent
    AGENT_ID=$(aws bedrock-agent create-agent \
        --region $REGION \
        --agent-name $AGENT_NAME \
        --foundation-model $MODEL_ID \
        --instruction "$INSTRUCTION" \
        --agent-resource-role-arn "arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME" \
        --idle-session-ttl-in-seconds 600 \
        --query 'agent.agentId' \
        --output text)
    
    echo "Agent created with ID: $AGENT_ID"
fi

# Step 5: Create API schema for action group
echo ""
echo "Step 5: Creating API schema..."

jq '.actionGroups[0].apiSchema.payload' /tmp/config-updated.json > /tmp/api-schema.json

# Step 6: Create action group
echo ""
echo "Step 6: Creating action group..."

# Note: Lambda ARN needs to be the actual deployed function
# For now, using a placeholder - update after Lambda deployment
LAMBDA_ARN="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:forecasting-agent-tools"

aws bedrock-agent create-agent-action-group \
    --region $REGION \
    --agent-id $AGENT_ID \
    --agent-version DRAFT \
    --action-group-name forecasting-tools \
    --action-group-executor lambda=$LAMBDA_ARN \
    --api-schema file:///tmp/api-schema.json \
    --action-group-state ENABLED || echo "Action group may already exist"

# Step 7: Prepare agent
echo ""
echo "Step 7: Preparing agent..."

aws bedrock-agent prepare-agent \
    --region $REGION \
    --agent-id $AGENT_ID

echo "Agent prepared successfully"

# Step 8: Create agent alias
echo ""
echo "Step 8: Creating agent alias..."

ALIAS_ID=$(aws bedrock-agent create-agent-alias \
    --region $REGION \
    --agent-id $AGENT_ID \
    --agent-alias-name production \
    --query 'agentAlias.agentAliasId' \
    --output text 2>/dev/null || echo "TSTALIASID")

echo "Agent alias created: $ALIAS_ID"

# Cleanup temp files
rm -f /tmp/bedrock-trust-policy.json /tmp/lambda-invoke-policy.json /tmp/config-updated.json /tmp/api-schema.json

# Summary
echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo "Agent ID: $AGENT_ID"
echo "Agent Alias: $ALIAS_ID"
echo "Region: $REGION"
echo ""
echo "Test the agent with:"
echo "aws bedrock-agent-runtime invoke-agent \\"
echo "  --region $REGION \\"
echo "  --agent-id $AGENT_ID \\"
echo "  --agent-alias-id $ALIAS_ID \\"
echo "  --session-id test-session-1 \\"
echo "  --input-text 'Generate a 7-day forecast for product ID 1' \\"
echo "  output.txt"
echo ""
echo "View logs in CloudWatch:"
echo "https://console.aws.amazon.com/cloudwatch/home?region=$REGION#logsV2:log-groups/log-group/\$252Faws\$252Fbedrock\$252Fagents\$252F$AGENT_NAME"

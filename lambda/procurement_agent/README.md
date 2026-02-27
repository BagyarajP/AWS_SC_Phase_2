# Procurement Bedrock Agent

## Overview

The Procurement Bedrock Agent is an autonomous AI agent powered by Claude 3.5 Sonnet that optimizes procurement decisions by analyzing inventory levels, demand forecasts, supplier performance, and cost factors.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Procurement Bedrock Agent                   │
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
        │ 5 Tools:
        │
        ├─► get_inventory_levels
        ├─► get_demand_forecast
        ├─► get_supplier_data
        ├─► calculate_eoq
        └─► create_purchase_order
```

## Agent Configuration

- **Agent Name**: `supply-chain-procurement-agent`
- **Model**: `anthropic.claude-3-5-sonnet-20241022-v2:0`
- **Region**: `us-east-1`
- **Action Group**: `procurement-tools` (5 Lambda tools)
- **Idle Session TTL**: 600 seconds (10 minutes)

## Decision-Making Process

The agent follows a systematic approach:

1. **Monitor Inventory**: Check inventory levels for products below reorder point
2. **Analyze Demand**: Retrieve demand forecasts to understand future requirements
3. **Evaluate Suppliers**: Compare suppliers based on performance metrics
4. **Calculate EOQ**: Determine optimal order quantity for cost optimization
5. **Create Purchase Order**: Generate PO with approval routing logic
6. **Provide Rationale**: Explain decision with confidence score

## Approval Routing Logic

Purchase orders are automatically routed based on risk assessment:

- **High-Risk** (requires approval):
  - Total value > £10,000
  - Confidence score < 0.7
  - Routes to `approval_queue` table
  - Requires Procurement Manager approval

- **Low-Risk** (auto-approved):
  - Total value ≤ £10,000
  - Confidence score ≥ 0.7
  - Creates PO directly in database
  - Logs to audit trail

## Lambda Tools

### 1. get_inventory_levels
Retrieves current inventory levels with reorder point analysis.

**Input**:
```json
{
  "warehouse_id": 1,
  "below_reorder_point_only": true
}
```

**Output**:
```json
{
  "inventory_records": [
    {
      "product_id": 123,
      "product_name": "Widget A",
      "quantity_on_hand": 45,
      "reorder_point": 100,
      "reorder_quantity": 200,
      "quantity_above_reorder": -55
    }
  ],
  "total_count": 15
}
```

### 2. get_demand_forecast
Retrieves demand forecasts for procurement planning.

**Input**:
```json
{
  "product_id": 123,
  "horizon_days": 30
}
```

**Output**:
```json
{
  "product_id": 123,
  "forecast_records": [...],
  "summary": {
    "total_forecast_demand": 3150.5,
    "average_daily_demand": 105.02
  }
}
```

### 3. get_supplier_data
Retrieves supplier performance metrics for comparison.

**Input**:
```json
{
  "product_id": 123
}
```

**Output**:
```json
{
  "suppliers": [
    {
      "supplier_id": 45,
      "supplier_name": "Acme Corp",
      "reliability_score": 0.95,
      "defect_rate": 0.02,
      "lead_time_days": 14,
      "unit_price": 25.50,
      "minimum_order_quantity": 100
    }
  ]
}
```

### 4. calculate_eoq
Calculates Economic Order Quantity for cost optimization.

**Input**:
```json
{
  "annual_demand": 10000,
  "order_cost": 100,
  "holding_cost": 5
}
```

**Output**:
```json
{
  "eoq": 632.46,
  "orders_per_year": 15.81,
  "total_annual_cost": 3162.28
}
```

### 5. create_purchase_order
Creates purchase order with automatic approval routing.

**Input**:
```json
{
  "product_id": 123,
  "supplier_id": 45,
  "quantity": 500,
  "unit_price": 25.50,
  "rationale": "Product below reorder point. Forecast shows 30-day demand of 3150 units. Selected supplier has 0.95 reliability score and competitive pricing.",
  "confidence_score": 0.85
}
```

**Output**:
```json
{
  "success": true,
  "status": "pending_approval",
  "total_value": 12750.00,
  "needs_approval": true,
  "approval_reason": "Total value £12,750.00 exceeds threshold of £10,000.00"
}
```

## System Prompt

The agent is instructed to:
- Monitor inventory levels and identify products below reorder points
- Analyze demand forecasts to determine optimal order quantities
- Evaluate supplier performance (reliability, pricing, lead time, defect rate)
- Calculate EOQ for cost optimization
- Create purchase orders with appropriate approval routing
- Provide detailed rationale for all procurement decisions

## Deployment

### Prerequisites

1. AWS CLI configured
2. IAM permissions for Bedrock, Lambda, IAM
3. Redshift Serverless workgroup running
4. Lambda functions deployed

### Deploy

```bash
cd lambda/procurement_agent
chmod +x deploy.sh
./deploy.sh
```

This will:
1. Deploy all 5 Lambda tools
2. Create IAM role for Bedrock Agent
3. Create Bedrock Agent
4. Configure action group with tools
5. Prepare agent for invocation

### Test

```bash
aws bedrock-agent-runtime invoke-agent \
  --region us-east-1 \
  --agent-id YOUR_AGENT_ID \
  --agent-alias-id TSTALIASID \
  --session-id test-1 \
  --input-text "Check inventory and create purchase orders for items below reorder point" \
  output.txt
```

## Example Workflow

**User Prompt**: "Check inventory and create purchase orders for items below reorder point"

**Agent Actions**:
1. Calls `get_inventory_levels` with `below_reorder_point_only=true`
2. For each low-inventory item:
   - Calls `get_demand_forecast` to understand future demand
   - Calls `get_supplier_data` to compare suppliers
   - Calls `calculate_eoq` to determine optimal quantity
   - Calls `create_purchase_order` with rationale and confidence score
3. Returns summary of actions taken

**Agent Response**:
```
I've analyzed the inventory and created purchase orders for 5 products below reorder point:

1. Widget A (Product ID: 123)
   - Current inventory: 45 units (reorder point: 100)
   - 30-day forecast: 3,150 units
   - Selected supplier: Acme Corp (reliability: 0.95, price: £25.50)
   - Order quantity: 500 units (EOQ optimized)
   - Total value: £12,750
   - Status: Pending approval (exceeds £10k threshold)
   - Confidence: 0.85

[... similar details for other products ...]

Summary:
- 5 purchase orders created
- 3 pending approval (high value)
- 2 auto-approved (low risk)
- Total procurement value: £45,230
```

## Monitoring

### CloudWatch Logs
- Agent: `/aws/bedrock/agents/supply-chain-procurement-agent`
- Lambda: `/aws/lambda/procurement-agent-tools`

### Metrics
- Purchase orders created
- Approval routing rate
- Supplier selection distribution
- Average confidence scores

## Requirements Validated

- **1.1**: Purchase order generation for low inventory
- **1.2**: Decision rationale completeness
- **1.3**: Confidence score validity
- **1.4**: High-risk decision routing
- **1.5**: Database persistence after approval
- **1.6**: Supplier selection optimality
- **1.7**: Agent decision audit logging
- **8.1**: Bedrock Agent configuration
- **8.2**: Agent scheduling
- **8.5**: Action group with Lambda tools
- **8.6**: CloudWatch logging

## Next Steps

1. Deploy Inventory Bedrock Agent (Task 6)
2. Implement property-based tests (Tasks 5.7-5.17)
3. Configure EventBridge scheduling (Task 14.2)
4. Integrate with Streamlit dashboard (Task 9)

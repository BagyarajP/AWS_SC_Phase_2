# Inventory Rebalancing Agent

Autonomous agent for inventory rebalancing across warehouses based on regional demand patterns.

## Overview

The Inventory Rebalancing Agent analyzes inventory distribution across warehouses and generates transfer recommendations to optimize stock levels based on forecasted demand. High-risk transfers (>100 units or confidence <0.75) are routed to human approval.

## Features

- **Imbalance Detection**: Calculates inventory-to-demand ratios across warehouses
- **Transfer Optimization**: Generates optimal transfer recommendations
- **Constraint Validation**: Respects source inventory and destination capacity limits
- **Explainable Decisions**: Natural language rationale for each transfer
- **Human-in-the-Loop**: Routes high-risk transfers to approval queue
- **Audit Logging**: Complete audit trail in Redshift

## Requirements Implemented

- Requirement 2.1: Inventory imbalance detection
- Requirement 2.2: Natural language rationale
- Requirement 2.3: Confidence score calculation
- Requirement 2.4: High-risk decision routing
- Requirement 2.5: Inventory record updates
- Requirement 2.6: Regional demand consideration
- Requirement 2.7: Audit logging

## Environment Variables

- `REDSHIFT_HOST`: Redshift cluster endpoint
- `REDSHIFT_PORT`: Redshift port (default: 5439)
- `REDSHIFT_DATABASE`: Database name (default: supply_chain)
- `REDSHIFT_USER`: Database user
- `REDSHIFT_PASSWORD`: Database password
- `LARGE_TRANSFER_THRESHOLD`: Transfer quantity threshold for approval (default: 100)
- `LOW_CONFIDENCE_THRESHOLD`: Confidence threshold for approval (default: 0.75)

## Deployment

```bash
# Package Lambda function
cd lambda/inventory_agent
zip -r inventory_agent.zip lambda_function.py

# Upload to AWS Lambda via Console
# Configure EventBridge trigger for daily execution at 3:00 AM UTC
```

## Testing

```bash
# Run property tests
pytest test_property_7_transfer_constraints.py -v

# Run with hypothesis statistics
pytest test_property_7_transfer_constraints.py -v --hypothesis-show-statistics
```

## Decision Logic

1. Query inventory levels across all warehouses
2. Fetch 7-day demand forecasts by warehouse
3. Calculate inventory-to-demand ratios
4. Identify imbalances (coefficient of variation > 0.3)
5. Generate transfer recommendations from excess to shortage warehouses
6. Calculate confidence score based on imbalance severity
7. Route to approval if quantity > 100 or confidence < 0.75
8. Execute approved transfers automatically
9. Log all decisions to audit log

## Example Output

```json
{
  "statusCode": 200,
  "body": {
    "successful_transfers": ["IT-20240115-a1b2c3d4"],
    "pending_approvals": ["IT-20240115-e5f6g7h8"],
    "failed": []
  }
}
```

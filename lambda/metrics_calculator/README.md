# Metrics Calculator Lambda Function

Calculates and stores inventory performance metrics and supplier performance metrics.

## Overview

The Metrics Calculator Lambda function runs periodically to calculate key performance indicators for inventory management and supplier performance. Metrics are stored in Redshift for historical analysis and dashboard display.

## Features

- **Inventory Turnover Calculation**: Sales value / average inventory value
- **Stockout Rate Tracking**: Stockout incidents / total demand events
- **Slow-Moving SKU Identification**: SKUs with turnover < 2.0
- **Supplier Reliability Scoring**: On-time deliveries / total deliveries
- **Supplier Lead Time Calculation**: Average delivery time
- **Decision Accuracy Tracking**: Compare predictions to actual outcomes
- **Metrics Persistence**: Store all metrics in Redshift with timestamps

## Requirements Implemented

- Requirement 13.1: Inventory turnover calculation
- Requirement 13.2: Stockout rate tracking
- Requirement 13.3: Inventory improvement measurement
- Requirement 13.5: Slow-moving SKU identification
- Requirement 13.7: Metrics persistence
- Requirement 14.1: Supplier reliability calculation
- Requirement 14.2: Supplier lead time calculation
- Requirement 14.7: Supplier metrics persistence
- Requirement 12.7: Decision accuracy tracking

## Environment Variables

- `REDSHIFT_HOST`: Redshift cluster endpoint
- `REDSHIFT_PORT`: Redshift port (default: 5439)
- `REDSHIFT_DATABASE`: Database name (default: supply_chain)
- `REDSHIFT_USER`: Database user
- `REDSHIFT_PASSWORD`: Database password

## Deployment

```bash
# Package Lambda function
cd lambda/metrics_calculator
zip -r metrics_calculator.zip lambda_function.py

# Upload to AWS Lambda via Console
# Configure EventBridge trigger for daily execution
# Set timeout to 15 minutes
# Attach SupplyChainAgentRole IAM role
```

## Metrics Calculated

### Inventory Metrics

1. **Inventory Turnover Ratio**
   - Formula: Total Sales Value / Average Inventory Value
   - Calculated per warehouse
   - 90-day measurement period

2. **Stockout Rate**
   - Formula: Stockout Incidents / Total Demand Events
   - Calculated per SKU
   - 90-day measurement period

3. **Slow-Moving SKUs**
   - Threshold: Turnover ratio < 2.0
   - 90-day measurement period

### Supplier Metrics

1. **Reliability Score**
   - Formula: On-Time Deliveries / Total Deliveries
   - 180-day measurement period

2. **Average Lead Time**
   - Formula: Mean(Delivery Date - Order Date)
   - 180-day measurement period

3. **Defect Rate**
   - Formula: Defective Units / Total Units Delivered
   - 180-day measurement period

### Decision Accuracy

1. **Accuracy Score**
   - Formula: 1 - |Actual - Predicted| / Predicted
   - Tracks agent decision accuracy over time

## Database Schema

### inventory_metrics Table

```sql
CREATE TABLE inventory_metrics (
    metric_id VARCHAR(50) PRIMARY KEY,
    warehouse_id VARCHAR(50),
    metric_name VARCHAR(100),
    metric_value DECIMAL(10,2),
    calculation_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### decision_accuracy Table

```sql
CREATE TABLE decision_accuracy (
    accuracy_id VARCHAR(50) PRIMARY KEY,
    decision_id VARCHAR(50),
    predicted_value DECIMAL(10,2),
    actual_value DECIMAL(10,2),
    accuracy_score DECIMAL(5,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Example Output

```json
{
  "statusCode": 200,
  "body": {
    "inventory_metrics": {
      "WH1_South": {
        "turnover_ratio": 4.2
      },
      "WH_Midland": {
        "turnover_ratio": 3.8
      },
      "WH_North": {
        "turnover_ratio": 4.5
      }
    },
    "supplier_metrics": {
      "SUP-0001": {
        "reliability_score": 0.95,
        "avg_lead_time": 7.5,
        "defect_rate": 0.02
      }
    },
    "slow_moving_skus": ["PROD-1234", "PROD-5678"],
    "errors": []
  }
}
```

## Testing

Property tests to be implemented:
- Property 35: Inventory turnover calculation
- Property 36: Stockout rate calculation
- Property 39: Metrics persistence
- Property 45: Supplier metrics persistence
- Property 34: Decision accuracy tracking

## Scheduling

Recommended EventBridge schedule: Daily at 4:00 AM UTC

```
cron(0 4 * * ? *)
```

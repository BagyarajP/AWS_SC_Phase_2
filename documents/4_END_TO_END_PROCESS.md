# Supply Chain AI Platform - End-to-End Process Document

**Project**: Supply Chain AI Platform (Bedrock + Agentic AI)  
**Version**: 1.0  
**Date**: February 2026  
**Audience**: Technical Teams, Operations, Management

---

## Executive Summary

This document describes the complete end-to-end processes for the Supply Chain AI Platform, from data ingestion through AI-powered decision-making to human approval and execution. The platform uses AWS Bedrock Agents with Claude 3.5 Sonnet to automate supply chain operations while maintaining human oversight for high-risk decisions.

---

## Table of Contents

1. [Data Ingestion Process](#1-data-ingestion-process)
2. [Forecasting Process](#2-forecasting-process)
3. [Procurement Process](#3-procurement-process)
4. [Inventory Rebalancing Process](#4-inventory-rebalancing-process)
5. [Approval Workflow](#5-approval-workflow)
6. [Audit and Compliance Process](#6-audit-and-compliance-process)
7. [Monitoring and Alerting](#7-monitoring-and-alerting)

---

## 1. Data Ingestion Process

### Overview
Daily batch process that extracts data from S3, transforms it, and loads it into Redshift Serverless.

### Process Flow

```
┌─────────────┐
│ Synthetic   │
│ Data Files  │
│   (CSV)     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  S3 Bucket  │
│ (us-east-1) │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  AWS Glue   │
│  ETL Job    │
└──────┬──────┘
       │
       ├─► Extract: Read CSV files
       ├─► Transform: Validate schema, convert types
       ├─► Load: COPY to Redshift via Data API
       │
       ▼
┌─────────────┐
│  Redshift   │
│ Serverless  │
└─────────────┘
```

### Step-by-Step Process

**Step 1: Data Generation** (One-time setup)
- Run `generate_synthetic_data.py`
- Generates 12 months of sales data
- Creates 2,000 SKUs, 500 suppliers, 3 warehouses
- Applies seasonality patterns (1.5x winter multiplier)
- Output: CSV files in `data/` directory

**Step 2: Upload to S3**
- Run `upload_to_s3.py`
- Uploads CSV files to S3 bucket
- Bucket: `supply-chain-data-{account-id}`
- Region: us-east-1

**Step 3: Glue ETL Execution** (Daily at midnight)
- **Trigger**: EventBridge schedule OR manual via AWS Console
- **Extract**: Read CSV files from S3
- **Transform**:
  - Validate schema against Redshift tables
  - Convert data types (String, Integer, Decimal, Date)
  - Handle NULL values (empty strings → NULL)
  - Filter invalid records (NULL primary keys)
- **Load**:
  - Stage data to S3 in Parquet format
  - Execute COPY command via Redshift Data API
  - Retry logic: 3 attempts with exponential backoff
  - Timeout: 5 minutes per table

**Step 4: Validation**
- Run `verify_data.py`
- Check row counts for all tables
- Verify referential integrity
- Validate seasonality patterns
- Check supplier metrics

**Step 5: Monitoring**
- CloudWatch metrics:
  - Records read
  - Records written
  - Records failed
  - Success rate
  - Processing time
- Alarms trigger on:
  - Job failure
  - Success rate < 95%
  - Processing time > 1 hour

### Error Handling

**Invalid Records**:
- Logged to CloudWatch
- Skipped (not loaded)
- Processing continues

**Connection Failures**:
- Retry 3 times with exponential backoff
- If all retries fail, job fails
- Alert sent to operations team

**Schema Mismatches**:
- Record logged to CloudWatch
- Record skipped
- Processing continues

### Success Criteria

✅ All CSV files processed  
✅ Success rate > 95%  
✅ All tables populated  
✅ Referential integrity maintained  
✅ Processing time < 1 hour  

---

## 2. Forecasting Process

### Overview
Daily automated process where the Forecasting Bedrock Agent generates demand forecasts for all 2,000 SKUs using Claude 3.5 Sonnet and statistical models.

### Process Flow

```
┌──────────────┐
│ EventBridge  │
│ (1:00 AM UTC)│
└──────┬───────┘
       │
       ▼
┌──────────────────────────────┐
│ Forecasting Bedrock Agent    │
│ (Claude 3.5 Sonnet)          │
└──────┬───────────────────────┘
       │
       ├─► Tool: get_historical_sales
       │   └─► Query 12 months of sales data
       │
       ├─► LLM Reasoning: Analyze patterns
       │
       ├─► Tool: calculate_forecast
       │   ├─► Holt-Winters exponential smoothing
       │   ├─► ARIMA forecasting
       │   ├─► Ensemble both models
       │   └─► Calculate confidence intervals (80%, 95%)
       │
       ├─► Tool: store_forecast
       │   └─► Insert into demand_forecast table
       │
       └─► Tool: calculate_accuracy
           └─► Calculate MAPE vs actual demand
```

### Step-by-Step Process

**Step 1: Agent Invocation** (Daily at 1:00 AM UTC)
- EventBridge triggers Bedrock Agent
- Input: "Generate 7-day and 30-day forecasts for all products"
- Agent uses Claude 3.5 Sonnet for reasoning

**Step 2: Historical Data Retrieval**
- Agent calls `get_historical_sales` tool
- Tool queries Redshift via Data API
- Returns 12 months of sales data per SKU
- Data includes: date, quantity, warehouse

**Step 3: LLM Analysis**
- Claude 3.5 Sonnet analyzes patterns:
  - Trend identification
  - Seasonality detection
  - Anomaly identification
  - Data quality assessment

**Step 4: Forecast Calculation**
- Agent calls `calculate_forecast` tool
- Tool applies statistical models:
  - **Holt-Winters**: Captures trend and seasonality
  - **ARIMA**: Captures autocorrelation
  - **Ensemble**: Weighted average of both models
- Calculates confidence intervals:
  - 80% confidence: ±1.28 standard deviations
  - 95% confidence: ±1.96 standard deviations
- Generates forecasts for:
  - 7-day horizon (short-term planning)
  - 30-day horizon (long-term planning)

**Step 5: Forecast Storage**
- Agent calls `store_forecast` tool
- Tool inserts records into `demand_forecast` table
- Each record includes:
  - Product ID
  - Forecast date
  - Forecast value
  - Confidence intervals (80%, 95%)
  - Horizon (7 or 30 days)
  - Timestamp

**Step 6: Accuracy Calculation**
- Agent calls `calculate_accuracy` tool
- Tool compares previous forecasts to actual demand
- Calculates MAPE (Mean Absolute Percentage Error)
- Stores results in `forecast_accuracy` table
- Target: MAPE < 15% for top 200 SKUs

**Step 7: Logging**
- All agent actions logged to CloudWatch
- Includes:
  - LLM reasoning steps
  - Tool invocations
  - Forecast metrics
  - Errors and warnings

### Output

**For Each SKU**:
- 7-day forecast (7 data points)
- 30-day forecast (30 data points)
- Confidence intervals for each point
- Accuracy metrics (MAPE)

**Total Daily Output**:
- 2,000 SKUs × 2 horizons = 4,000 forecasts
- ~74,000 data points (37 points × 2,000 SKUs)

### Success Criteria

✅ All 2,000 SKUs forecasted  
✅ MAPE < 15% for top 200 SKUs  
✅ Confidence intervals calculated  
✅ Forecasts stored in Redshift  
✅ Processing time < 2 hours  

---

## 3. Procurement Process

### Overview
Daily automated process where the Procurement Bedrock Agent creates purchase orders based on inventory levels, demand forecasts, and supplier performance.

### Process Flow

```
┌──────────────┐
│ EventBridge  │
│ (2:00 AM UTC)│
└──────┬───────┘
       │
       ▼
┌──────────────────────────────┐
│ Procurement Bedrock Agent    │
│ (Claude 3.5 Sonnet)          │
└──────┬───────────────────────┘
       │
       ├─► Tool: get_inventory_levels
       │   └─► Find SKUs below reorder point
       │
       ├─► Tool: get_demand_forecast
       │   └─► Get 30-day forecast
       │
       ├─► Tool: get_supplier_data
       │   └─► Get supplier performance metrics
       │
       ├─► LLM Reasoning: Evaluate suppliers
       │   └─► Weighted scoring (40% price, 30% reliability, 30% lead time)
       │
       ├─► Tool: calculate_eoq
       │   └─► Determine optimal order quantity
       │
       ├─► LLM Reasoning: Generate rationale + confidence
       │
       └─► Tool: create_purchase_order
           ├─► If high-risk → Approval queue
           └─► If low-risk → Create PO directly
```

### Step-by-Step Process

**Step 1: Agent Invocation** (Daily at 2:00 AM UTC)
- EventBridge triggers Bedrock Agent
- Input: "Check inventory and create purchase orders for items below reorder point"

**Step 2: Inventory Analysis**
- Agent calls `get_inventory_levels` tool
- Parameters: `below_reorder_point_only=true`
- Returns list of SKUs needing replenishment
- Typical result: 50-100 SKUs per day

**Step 3: Demand Forecast Retrieval**
- For each low-inventory SKU:
  - Agent calls `get_demand_forecast` tool
  - Parameters: `product_id`, `horizon_days=30`
  - Returns 30-day forecast with confidence intervals

**Step 4: Supplier Evaluation**
- Agent calls `get_supplier_data` tool
- Returns all suppliers for the SKU with:
  - Unit price
  - Reliability score (0-1)
  - Lead time (days)
  - Defect rate
  - Minimum order quantity

**Step 5: LLM Supplier Selection**
- Claude 3.5 Sonnet evaluates suppliers using weighted criteria:
  - **40% Price**: Lower is better
  - **30% Reliability**: Higher is better (target > 0.85)
  - **30% Lead Time**: Shorter is better
- Generates natural language explanation
- Example: "Selected Supplier A due to 95% reliability score and competitive pricing at £25.50/unit, despite 2-day longer lead time than Supplier B"

**Step 6: Order Quantity Calculation**
- Agent calls `calculate_eoq` tool
- Inputs:
  - Annual demand (from forecast)
  - Order cost (fixed cost per order)
  - Holding cost (cost to store per unit per year)
- Returns optimal order quantity (EOQ)
- Balances ordering costs vs holding costs

**Step 7: Decision Generation**
- LLM generates:
  - **Rationale**: Natural language explanation
  - **Confidence Score**: 0-1 based on:
    - Forecast accuracy (MAPE)
    - Supplier reliability
    - Data completeness
  - **Decision Factors**: Top 3 influencing factors

**Step 8: Approval Routing**
- Agent calls `create_purchase_order` tool
- Tool checks thresholds:
  - **High-Risk** (requires approval):
    - Total value > £10,000
    - Confidence score < 0.7
  - **Low-Risk** (auto-approved):
    - Total value ≤ £10,000
    - Confidence score ≥ 0.7

**Step 9: Execution**
- **If High-Risk**:
  - Insert into `approval_queue` table
  - Assign to Procurement Manager role
  - Include rationale and confidence score
  - Send notification (optional)
- **If Low-Risk**:
  - Insert into `purchase_order_header` table
  - Insert into `purchase_order_line` table
  - Update inventory expected quantities

**Step 10: Audit Logging**
- All decisions logged to `audit_log` table
- Includes:
  - Agent name
  - Decision type
  - Rationale
  - Confidence score
  - Timestamp
  - Approval status

### Output

**Daily Output**:
- 50-100 purchase orders created
- ~30% require approval (high-risk)
- ~70% auto-approved (low-risk)
- Total procurement value: £30,000-50,000

### Success Criteria

✅ All low-inventory SKUs processed  
✅ Supplier selection optimized  
✅ EOQ calculated for all orders  
✅ High-risk orders routed to approval  
✅ All decisions logged to audit trail  

---

## 4. Inventory Rebalancing Process

### Overview
Daily automated process where the Inventory Bedrock Agent recommends stock transfers across warehouses to optimize distribution.

### Process Flow

```
┌──────────────┐
│ EventBridge  │
│ (3:00 AM UTC)│
└──────┬───────┘
       │
       ▼
┌──────────────────────────────┐
│ Inventory Bedrock Agent      │
│ (Claude 3.5 Sonnet)          │
└──────┬───────────────────────┘
       │
       ├─► Tool: get_warehouse_inventory
       │   └─► Get inventory across all warehouses
       │
       ├─► Tool: get_regional_forecasts
       │   └─► Get 7-day forecast by warehouse
       │
       ├─► Tool: calculate_imbalance_score
       │   └─► Calculate inventory-to-demand ratio
       │
       ├─► LLM Reasoning: Identify optimal transfers
       │   └─► Minimize costs while meeting demand
       │
       └─► Tool: execute_transfer
           ├─► If high-risk → Approval queue
           └─► If low-risk → Execute transfer
```

### Step-by-Step Process

**Step 1: Agent Invocation** (Daily at 3:00 AM UTC)
- EventBridge triggers Bedrock Agent
- Input: "Analyze inventory and recommend transfers to balance stock"

**Step 2: Inventory Analysis**
- Agent calls `get_warehouse_inventory` tool
- Returns inventory levels for all SKUs across 3 warehouses:
  - South Warehouse
  - Midland Warehouse
  - North Warehouse

**Step 3: Regional Forecast Retrieval**
- Agent calls `get_regional_forecasts` tool
- Parameters: `horizon_days=7` (short-term planning)
- Returns demand forecast by warehouse

**Step 4: Imbalance Calculation**
- Agent calls `calculate_imbalance_score` tool
- Tool calculates for each SKU:
  - Inventory-to-demand ratio per warehouse
  - Identifies excess (ratio > 2.0)
  - Identifies shortage (ratio < 0.5)
- Returns imbalance score (0-100, higher = more imbalanced)

**Step 5: LLM Transfer Planning**
- Claude 3.5 Sonnet analyzes:
  - Which warehouses have excess
  - Which warehouses have shortage
  - Transfer costs (distance, handling)
  - Warehouse capacity constraints
- Generates transfer recommendations:
  - Source warehouse
  - Destination warehouse
  - Quantity to transfer
  - Rationale

**Step 6: Decision Generation**
- LLM generates:
  - **Rationale**: Natural language explanation
  - **Confidence Score**: 0-1 based on:
    - Forecast accuracy
    - Historical transfer success
    - Capacity constraints
  - **Decision Factors**: Imbalance score, regional demand, costs

**Step 7: Approval Routing**
- Agent calls `execute_transfer` tool
- Tool checks thresholds:
  - **High-Risk** (requires approval):
    - Transfer quantity > 100 units
    - Confidence score < 0.75
  - **Low-Risk** (auto-approved):
    - Transfer quantity ≤ 100 units
    - Confidence score ≥ 0.75

**Step 8: Execution**
- **If High-Risk**:
  - Insert into `approval_queue` table
  - Assign to Inventory Manager role
- **If Low-Risk**:
  - Update `inventory` table (source warehouse: -quantity)
  - Update `inventory` table (destination warehouse: +quantity)
  - Create transfer record

**Step 9: Audit Logging**
- All decisions logged to `audit_log` table

### Output

**Daily Output**:
- 20-30 transfer recommendations
- ~40% require approval (high-risk)
- ~60% auto-approved (low-risk)

### Success Criteria

✅ All imbalances identified  
✅ Transfer recommendations optimized  
✅ Warehouse capacity respected  
✅ High-risk transfers routed to approval  
✅ All decisions logged  

---

## 5. Approval Workflow

### Overview
Human-in-the-loop process for reviewing and approving high-risk AI decisions.

### Process Flow

```
┌──────────────────┐
│ High-Risk        │
│ Decision         │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Approval Queue   │
│ (Redshift Table) │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Streamlit        │
│ Dashboard        │
└────────┬─────────┘
         │
         ├─► View: Rationale, confidence, data
         │
         ├─► Action: Approve / Reject / Modify
         │
         ▼
┌──────────────────┐
│ Execute Decision │
│ OR Cancel        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Audit Log        │
└──────────────────┘
```

### Step-by-Step Process

**Step 1: Decision Routing**
- Agent determines decision is high-risk
- Inserts record into `approval_queue` table
- Fields:
  - Decision ID
  - Agent name
  - Decision type (PO or Transfer)
  - Rationale (LLM-generated)
  - Confidence score
  - Decision data (JSON)
  - Assigned role
  - Status: "pending"

**Step 2: Dashboard Display**
- User logs into Streamlit dashboard
- Dashboard queries `approval_queue` table
- Filters by user role:
  - Procurement Manager: Purchase orders
  - Inventory Manager: Transfers
- Displays pending approvals with:
  - Summary (SKU, quantity, value/units)
  - AI rationale
  - Confidence score
  - Decision factors
  - Supporting data

**Step 3: User Review**
- User reads AI rationale
- Reviews supporting data:
  - Inventory levels
  - Demand forecast
  - Supplier performance (for POs)
  - Warehouse capacity (for transfers)
- Can ask AI for clarification via chat interface

**Step 4: User Decision**
- **Option 1: Approve**
  - Click "Approve" button
  - Decision executes immediately
  - Record updated in `approval_queue`: status="approved"
  - Action executed (PO created or transfer executed)
  
- **Option 2: Reject**
  - Click "Reject" button
  - Enter rejection reason
  - Record updated in `approval_queue`: status="rejected"
  - Action cancelled
  
- **Option 3: Modify**
  - Click "Modify" button
  - Edit decision parameters (quantity, supplier, etc.)
  - Submit modified decision
  - Modified decision executes
  - Original and modified versions logged

**Step 5: Execution**
- If approved:
  - Lambda tool invoked to execute action
  - Database updated (PO created or inventory transferred)
  - Confirmation displayed to user
- If rejected:
  - No action taken
  - Rejection reason stored

**Step 6: Audit Logging**
- All approvals/rejections logged to `audit_log` table
- Includes:
  - User name
  - Action (approve/reject/modify)
  - Timestamp
  - Reason (for rejections)
  - Before/after states (for modifications)

### Approval Metrics

**Target SLAs**:
- Review time: < 24 hours
- Approval rate: 80-90%
- Rejection rate: 10-20%

**Typical Volume**:
- Purchase orders: 15-30 per day
- Transfers: 8-12 per day
- Total: 23-42 approvals per day

### Success Criteria

✅ All high-risk decisions routed to approval  
✅ Users can view rationale and data  
✅ Approval/rejection executed correctly  
✅ All actions logged to audit trail  

---

## 6. Audit and Compliance Process

### Overview
Continuous process that logs all agent decisions, human actions, and data modifications for compliance and investigation.

### What Gets Logged

**Agent Decisions**:
- Agent name
- Decision type
- Rationale (LLM-generated)
- Confidence score
- Decision data
- Timestamp

**Human Actions**:
- User name
- Action type (approve/reject/modify)
- Reason
- Timestamp

**Data Modifications**:
- Entity type (PO, inventory, etc.)
- Entity ID
- Before state (JSON)
- After state (JSON)
- Timestamp

### Audit Log Schema

```sql
CREATE TABLE audit_log (
    event_id VARCHAR(50) PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent_name VARCHAR(100),
    user_name VARCHAR(100),
    action_type VARCHAR(100),
    entity_type VARCHAR(100),
    entity_id VARCHAR(50),
    rationale TEXT,
    confidence_score DECIMAL(3,2),
    before_state JSON,
    after_state JSON,
    metadata JSON
);
```

### Query Capabilities

**Search by Date Range**:
```sql
SELECT * FROM audit_log
WHERE timestamp BETWEEN '2026-01-01' AND '2026-01-31';
```

**Filter by Agent**:
```sql
SELECT * FROM audit_log
WHERE agent_name = 'Procurement';
```

**Filter by User**:
```sql
SELECT * FROM audit_log
WHERE user_name = 'john.smith@company.com';
```

**Export to CSV**:
- Dashboard provides "Export" button
- Generates CSV file with all audit records
- Includes all fields and LLM-generated explanations

### Retention Policy

- **Minimum**: 7 years (compliance requirement)
- **Storage**: Redshift Serverless
- **Backup**: Automated snapshots (7-day retention)
- **Archive**: S3 Glacier for long-term storage

### Success Criteria

✅ All decisions logged  
✅ All approvals/rejections logged  
✅ All data modifications logged  
✅ Search and filter capabilities working  
✅ CSV export functional  
✅ 7-year retention maintained  

---

## 7. Monitoring and Alerting

### CloudWatch Dashboards

**1. Bedrock Agents Dashboard**:
- Agent invocation count
- Tool call success rate
- Average response time
- Token usage and costs
- Error rate

**2. Data Pipeline Dashboard**:
- Glue job success rate
- ETL processing time
- Record counts (read/written/failed)
- Redshift query performance

**3. Application Dashboard**:
- Streamlit active users
- Dashboard load time
- API response times
- Error rates

### CloudWatch Alarms

**Critical Alarms** (PagerDuty integration):
- Bedrock Agent failures (> 5/hour)
- Glue job failures (any)
- Redshift high RPU usage (> 80%)
- Lambda errors (> 1% error rate)

**Warning Alarms** (Email notification):
- Forecast MAPE > 20%
- Approval queue backlog > 50
- Dashboard response time > 5 seconds

### Metrics Tracked

**Business Metrics**:
- Forecasts generated per day
- Purchase orders created per day
- Transfers executed per day
- Approval rate
- Average confidence score

**Technical Metrics**:
- Agent response time
- Tool invocation latency
- Redshift query time
- Dashboard load time
- Error rates

**Cost Metrics**:
- Bedrock token usage
- Redshift RPU hours
- Lambda invocations
- S3 storage
- Total daily cost

### Success Criteria

✅ All dashboards operational  
✅ All alarms configured  
✅ PagerDuty integration working  
✅ Metrics tracked and visualized  
✅ Cost monitoring enabled  

---

## Summary

The Supply Chain AI Platform operates through seven interconnected processes:

1. **Data Ingestion**: Daily ETL from S3 to Redshift
2. **Forecasting**: AI-powered demand prediction for all SKUs
3. **Procurement**: Automated purchase order creation with supplier selection
4. **Inventory Rebalancing**: Automated stock transfers across warehouses
5. **Approval Workflow**: Human review of high-risk decisions
6. **Audit and Compliance**: Complete logging of all actions
7. **Monitoring and Alerting**: Real-time visibility and alerting

All processes are fully automated with human oversight for high-risk decisions, ensuring optimal supply chain operations while maintaining control and compliance.

---

**Document Status**: APPROVED  
**Last Updated**: February 2026  
**Next Review**: Post-deployment (3 months)

# Supply Chain AI Platform - Design Document

**Project**: Supply Chain AI Platform (Bedrock + Agentic AI)  
**Version**: 1.0  
**Date**: February 2026  
**Status**: Complete - Production Ready

---

## Executive Summary

This document describes the technical design for an MVP autonomous AI-powered supply chain optimization platform using AWS Bedrock Agents with Claude 3.5 Sonnet foundation model. The system employs an agentic AI architecture where autonomous agents make decisions with human oversight for high-risk actions.

---

## Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Supply Chain AI Platform                      │
│                  (AWS Bedrock + Agentic AI)                     │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Forecasting    │     │   Procurement    │     │    Inventory     │
│  Bedrock Agent   │     │  Bedrock Agent   │     │  Bedrock Agent   │
│  (Claude 3.5)    │     │  (Claude 3.5)    │     │  (Claude 3.5)    │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                        │                        │
         │ 4 Lambda Tools         │ 5 Lambda Tools         │ 4 Lambda Tools
         │                        │                        │
         └────────────────────────┴────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
         ┌──────────▼──────────┐    ┌──────────▼──────────┐
         │  Redshift Serverless │    │  Streamlit Dashboard│
         │  (32 RPUs, us-east-1)│    │  (SageMaker)        │
         └─────────────────────┘    └─────────────────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
    ┌────▼────┐         ┌─────▼─────┐
    │ AWS Glue│         │EventBridge│
    │ ETL Job │         │ Schedules │
    └─────────┘         └───────────┘
```

### Key Design Principles

1. **Gen AI First**: AWS Bedrock foundation models (Claude 3.5 Sonnet) for reasoning and decision-making
2. **Agentic AI Architecture**: Autonomous agents with tool-calling capabilities
3. **Explainability First**: Every decision includes natural language rationale
4. **Human-in-the-Loop**: High-risk decisions route to approval queues
5. **Audit Everything**: Immutable audit log for compliance
6. **Serverless Simplicity**: No infrastructure management
7. **Single Region**: All resources in us-east-1 (N. Virginia)

---

## Component Design

### 1. Redshift Serverless Data Warehouse

**Configuration**:
- **Deployment**: Redshift Serverless workgroup in us-east-1
- **Base Capacity**: 32 RPUs (Redshift Processing Units)
- **Scaling**: Auto-scales based on workload
- **Namespace**: supply-chain-platform
- **Workgroup**: supply-chain-workgroup

**Schema Design** (13 Tables):

1. **product** - Product catalog (2,000 SKUs)
2. **warehouse** - Warehouse locations (3 warehouses)
3. **supplier** - Supplier information (500 suppliers)
4. **inventory** - Current stock levels
5. **purchase_order_header** - PO headers
6. **purchase_order_line** - PO line items
7. **sales_order_header** - Sales order headers
8. **sales_order_line** - Sales order line items
9. **agent_decision** - Agent decisions with rationale
10. **approval_queue** - Pending approvals
11. **audit_log** - Complete audit trail
12. **demand_forecast** - Forecast data
13. **forecast_accuracy** - Accuracy metrics

**Connection Pattern**:
- Lambda functions use `redshift-data` API (serverless, no connection pooling)
- IAM-based authentication (no passwords)
- Automatic scaling for concurrent queries

---

### 2. AWS Bedrock Agents

**Foundation Model**: anthropic.claude-3-5-sonnet-20241022-v2:0  
**Region**: us-east-1 (N. Virginia)

#### Forecasting Bedrock Agent

**Purpose**: Generate demand forecasts for all SKUs

**Trigger**: EventBridge daily at 1:00 AM UTC

**Lambda Tools** (4):
1. `get_historical_sales` - Retrieve 12 months of sales data
2. `calculate_forecast` - Holt-Winters + ARIMA ensemble
3. `store_forecast` - Persist forecasts to Redshift
4. `calculate_accuracy` - Calculate MAPE

**System Prompt**:
```
You are an autonomous demand forecasting agent. Generate accurate forecasts 
for all SKUs using historical data and statistical models. Provide confidence 
intervals at 80% and 95% levels. Support 7-day and 30-day horizons.
```

**Decision Flow**:
1. Retrieve historical sales data (12 months)
2. Apply Holt-Winters exponential smoothing
3. Apply ARIMA forecasting
4. Ensemble both models
5. Calculate confidence intervals
6. Store forecasts in Redshift
7. Calculate accuracy metrics (MAPE)

---

#### Procurement Bedrock Agent

**Purpose**: Automate purchase order creation with supplier selection

**Trigger**: EventBridge daily at 2:00 AM UTC

**Lambda Tools** (5):
1. `get_inventory_levels` - Query inventory with filters
2. `get_demand_forecast` - Retrieve forecasts
3. `get_supplier_data` - Supplier performance metrics
4. `calculate_eoq` - Economic Order Quantity
5. `create_purchase_order` - PO creation with approval routing

**System Prompt**:
```
You are an autonomous procurement agent. Analyze inventory levels, demand 
forecasts, and supplier performance. Generate purchase orders with clear 
rationale. Route high-risk decisions (value > £10k OR confidence < 0.7) 
to approval queue.
```

**Approval Routing Logic**:
- **High-Risk** (requires approval):
  - Total value > £10,000
  - Confidence score < 0.7
- **Low-Risk** (auto-approved):
  - Total value ≤ £10,000
  - Confidence score ≥ 0.7

**Decision Flow**:
1. Check inventory levels (below reorder point)
2. Retrieve 30-day demand forecast
3. Evaluate suppliers (price, reliability, lead time)
4. Calculate EOQ for optimal quantity
5. Generate rationale and confidence score
6. Create PO or route to approval queue
7. Log decision to audit trail

---

#### Inventory Bedrock Agent

**Purpose**: Automate inventory rebalancing across warehouses

**Trigger**: EventBridge daily at 3:00 AM UTC

**Lambda Tools** (4):
1. `get_warehouse_inventory` - Query inventory across warehouses
2. `get_regional_forecasts` - Regional demand forecasts
3. `calculate_imbalance_score` - Inventory imbalance metrics
4. `execute_transfer` - Transfer execution with approval routing

**System Prompt**:
```
You are an autonomous inventory rebalancing agent. Analyze inventory across 
warehouses and regional demand. Generate transfer recommendations to optimize 
distribution. Route high-risk decisions (quantity > 100 OR confidence < 0.75) 
to approval queue.
```

**Approval Routing Logic**:
- **High-Risk** (requires approval):
  - Transfer quantity > 100 units
  - Confidence score < 0.75
- **Low-Risk** (auto-approved):
  - Transfer quantity ≤ 100 units
  - Confidence score ≥ 0.75

**Decision Flow**:
1. Query inventory across all warehouses
2. Retrieve regional demand forecasts (7-day)
3. Calculate imbalance scores
4. Generate transfer recommendations
5. Generate rationale and confidence score
6. Execute transfer or route to approval queue
7. Log decision to audit trail

---

### 3. Lambda Tools

**Purpose**: Provide data access and business logic for Bedrock Agents

**Architecture**:
- **Runtime**: Python 3.9+
- **Connection**: Redshift Data API (serverless)
- **Authentication**: IAM roles
- **Logging**: CloudWatch
- **Timeout**: 5 minutes per tool

**Common Pattern**:
```python
import boto3
import json

redshift_data = boto3.client('redshift-data', region_name='us-east-1')

def lambda_handler(event, context):
    # Extract parameters from Bedrock Agent
    # Execute SQL via Redshift Data API
    # Return results in JSON format
    # Log to CloudWatch
```

**Total Tools**: 13 Lambda functions across 3 agents

---

### 4. AWS Glue ETL Job

**Purpose**: Extract, transform, and load data from S3 to Redshift

**Configuration**:
- **Job Type**: Python Shell
- **Python Version**: 3.9
- **Schedule**: Daily batch processing
- **Source**: S3 buckets (CSV files)
- **Destination**: Redshift Serverless

**ETL Process**:
1. **Extract**: Read CSV files from S3
2. **Transform**: 
   - Schema validation
   - Data type conversions
   - NULL handling
   - Primary key filtering
3. **Load**: 
   - Stage to S3 (Parquet)
   - COPY to Redshift via Data API
   - Retry logic (3 attempts)
4. **Monitor**:
   - CloudWatch metrics
   - Record counts
   - Success rate

**Error Handling**:
- Skip invalid records
- Log errors to CloudWatch
- Continue processing valid data

---

### 5. Streamlit Dashboard (SageMaker)

**Purpose**: Web interface for monitoring and approvals

**Deployment**:
- **Platform**: Amazon SageMaker Notebook
- **Instance Type**: ml.t3.medium
- **Region**: us-east-1

**Features**:

**Procurement Manager Dashboard**:
- Pending approvals with AI rationale
- Recent purchase orders (30 days)
- Supplier performance scorecards
- AI chat interface
- Approval actions (Approve/Reject/Modify)

**Inventory Manager Dashboard**:
- Pending transfer approvals
- Inventory levels heatmap
- Forecast accuracy (MAPE by SKU)
- Inventory metrics (turnover, stockout rate)
- AI chat interface

**UI Theme**:
- Glassy design with backdrop blur
- Gradient background
- Modern card-based layout
- Responsive design

**Data Connection**:
- Redshift Data API for queries
- Bedrock Runtime API for chat
- Bedrock Agent Runtime for agent invocations

---

### 6. EventBridge Scheduling

**Purpose**: Trigger Bedrock Agents daily

**Schedules**:
1. **Forecasting Agent**: Daily at 1:00 AM UTC
2. **Procurement Agent**: Daily at 2:00 AM UTC
3. **Inventory Agent**: Daily at 3:00 AM UTC

**Configuration**:
```json
{
  "ScheduleExpression": "cron(0 1 * * ? *)",
  "Target": "arn:aws:bedrock:us-east-1:ACCOUNT_ID:agent/AGENT_ID",
  "Input": "{\"inputText\": \"Generate forecasts for all products\"}"
}
```

---

### 7. IAM Security

**IAM Roles** (4):

1. **SupplyChainBedrockAgentRole**
   - Permissions: bedrock:InvokeModel, lambda:InvokeFunction
   - Used by: Bedrock Agents

2. **SupplyChainToolRole**
   - Permissions: redshift-data:*, logs:*
   - Used by: Lambda tools

3. **SupplyChainGlueRole**
   - Permissions: s3:*, redshift-data:*, logs:*
   - Used by: Glue ETL job

4. **SupplyChainStreamlitRole**
   - Permissions: bedrock:*, redshift-data:*, lambda:*
   - Used by: SageMaker notebook

**Security Features**:
- Least privilege policies
- Resource-specific ARNs
- CloudWatch logging for all authentication
- No hardcoded credentials

---

## Data Flow

### End-to-End Flow

1. **Data Ingestion**:
   - Synthetic data → S3
   - Glue ETL → Transform
   - Load → Redshift Serverless

2. **Agent Execution**:
   - EventBridge → Trigger agent
   - Bedrock Agent → LLM reasoning
   - Agent → Call Lambda tools
   - Tools → Query/Update Redshift
   - Agent → Generate decision + rationale

3. **Decision Routing**:
   - Low-risk → Execute automatically
   - High-risk → Approval queue
   - User → Review in dashboard
   - Approve → Execute via tools
   - Reject → Cancel + log reason

4. **Audit Trail**:
   - All decisions → audit_log table
   - All approvals → audit_log table
   - All data changes → audit_log table
   - Retention: 7 years

---

## Scalability & Performance

### Current Capacity (MVP)
- **SKUs**: 2,000
- **Suppliers**: 500
- **Warehouses**: 3
- **Concurrent Users**: 50
- **Daily Forecasts**: 4,000 (2 horizons × 2,000 SKUs)

### Scaling Strategy
- **Redshift**: Auto-scales RPUs based on workload
- **Lambda**: Automatic scaling (1,000 concurrent executions)
- **Bedrock**: AWS-managed scaling
- **SageMaker**: Vertical scaling (upgrade instance type)

### Performance Targets
- Agent response: < 30 seconds (95th percentile)
- Dashboard load: < 3 seconds
- Forecast generation: < 2 hours for all SKUs
- Redshift queries: < 5 seconds (95th percentile)

---

## Monitoring & Observability

### CloudWatch Dashboards

1. **Bedrock Agents Dashboard**:
   - Invocation count
   - Tool call success rate
   - Response time
   - Token usage

2. **Data Pipeline Dashboard**:
   - Glue job success rate
   - ETL processing time
   - Record counts
   - Redshift query performance

3. **Application Dashboard**:
   - Active users
   - Dashboard load time
   - API response times
   - Error rates

### CloudWatch Alarms

- Bedrock Agent failures (> 5/hour)
- Glue job failures (any)
- Redshift high RPU usage (> 80%)
- Lambda errors (> 1% error rate)

---

## Cost Optimization

### Monthly Cost Breakdown

| Component | Cost | Optimization |
|-----------|------|--------------|
| Redshift Serverless | $50-100 | Auto-pause when idle |
| Bedrock (Claude 3.5) | $1,260 | Cache frequent queries |
| Lambda | Free | Free tier covers usage |
| S3 Storage | $5 | Lifecycle policies |
| SageMaker | $36 | Stop when not in use |
| EventBridge | <$1 | Minimal events |
| CloudWatch | $10 | 7-day retention |
| **TOTAL** | **$1,361-1,411** | |

### Cost Optimization Tips

1. Enable Redshift auto-pause (saves ~70%)
2. Use Lambda reserved concurrency
3. Cache Bedrock responses
4. Stop SageMaker instance when not in use
5. Set CloudWatch log retention to 7 days

---

## Disaster Recovery

### Backup Strategy

- **Redshift**: Automated snapshots (7-day retention)
- **S3**: Versioning enabled
- **Lambda**: Code stored in version control
- **Bedrock Agents**: Configuration in IaC

### Recovery Objectives

- **RTO** (Recovery Time Objective): 4 hours
- **RPO** (Recovery Point Objective): 24 hours

### Recovery Procedures

1. Restore Redshift from snapshot
2. Redeploy Lambda functions from code
3. Recreate Bedrock Agents from configuration
4. Restart Streamlit dashboard
5. Verify data integrity

---

## Security Architecture

### Data Protection

- **Encryption at Rest**: AES-256 (all services)
- **Encryption in Transit**: TLS 1.2+ (all connections)
- **Key Management**: AWS KMS
- **No PII**: System does not store personal data

### Access Control

- **Authentication**: AWS IAM
- **Authorization**: Role-based (Procurement Manager, Inventory Manager)
- **Audit**: All access logged to CloudWatch
- **MFA**: Recommended for production

### Compliance

- **GDPR**: Data residency configurable
- **SOC 2 Type II**: AWS infrastructure certified
- **Audit Trail**: 7-year retention
- **Data Retention**: Configurable per table

---

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|------------|---------|
| **AI/ML** | AWS Bedrock (Claude 3.5 Sonnet) | LLM reasoning and decision-making |
| **Agents** | Bedrock Agents | Autonomous decision-making |
| **Compute** | AWS Lambda | Agent tools and business logic |
| **Data Warehouse** | Redshift Serverless | Operational data storage |
| **ETL** | AWS Glue | Data transformation |
| **Storage** | Amazon S3 | Data staging |
| **UI** | Streamlit on SageMaker | Web dashboard |
| **Orchestration** | EventBridge | Agent scheduling |
| **Security** | AWS IAM | Access control |
| **Monitoring** | CloudWatch | Logs and metrics |
| **Region** | us-east-1 | N. Virginia |

---

## Design Decisions

### Why Bedrock Agents?
- Native LLM integration with Claude 3.5 Sonnet
- Built-in tool-calling capabilities
- Managed infrastructure (no servers)
- Automatic scaling
- Natural language reasoning

### Why Redshift Serverless?
- No infrastructure management
- Auto-scaling based on workload
- Data API for serverless connectivity
- Cost-effective for MVP scale
- Integrated with AWS ecosystem

### Why Lambda for Tools?
- Stateless and scalable
- Pay-per-use pricing
- Easy integration with Bedrock Agents
- Fast cold start times
- Managed runtime

### Why Streamlit on SageMaker?
- Rapid UI development
- Python-native (matches backend)
- Easy Bedrock integration
- Managed hosting
- Cost-effective for MVP

---

## Future Enhancements

### Phase 2 (Post-MVP)

1. **Multi-Region Deployment**: Expand to eu-west-1 for EU customers
2. **Advanced Analytics**: Real-time dashboards with streaming data
3. **Mobile App**: Native iOS/Android apps
4. **API Gateway**: REST API for third-party integrations
5. **Machine Learning**: Custom ML models for forecasting
6. **Advanced Guardrails**: Content filtering and safety controls

### Phase 3 (Scale)

1. **10,000+ SKUs**: Scale to enterprise level
2. **Global Warehouses**: Support 50+ warehouses
3. **Real-Time Processing**: Stream processing with Kinesis
4. **Advanced AI**: Multi-agent collaboration
5. **Predictive Maintenance**: Equipment failure prediction
6. **Supply Chain Network**: Multi-tier supplier management

---

**Document Status**: APPROVED  
**Last Updated**: February 2026  
**Next Review**: Post-deployment (3 months)

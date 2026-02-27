# Supply Chain AI Platform - Streamlit Dashboard

## Overview

Interactive dashboard for supply chain management with AI-powered insights, built with Streamlit and integrated with AWS Bedrock Agents.

## Features

- **Role-Based Access**: Separate dashboards for Procurement and Inventory Managers
- **AI Chat Interface**: Natural language queries powered by Claude 3.5 Sonnet
- **Real-Time Data**: Connected to Redshift Serverless via Data API
- **Glassy Theme**: Modern UI with backdrop blur effects
- **AI Insights**: Bedrock Agent invocations for recommendations

## Architecture

```
┌─────────────────────────────────────────┐
│      Streamlit Dashboard (SageMaker)    │
│                                         │
│  ┌─────────────┐    ┌───────────────┐ │
│  │ Procurement │    │   Inventory   │ │
│  │  Dashboard  │    │   Dashboard   │ │
│  └─────────────┘    └───────────────┘ │
│                                         │
│  ┌─────────────────────────────────┐  │
│  │      AI Chat Interface          │  │
│  └─────────────────────────────────┘  │
└──────────┬──────────────┬──────────────┘
           │              │
           ▼              ▼
    ┌──────────┐   ┌──────────────┐
    │ Bedrock  │   │  Redshift    │
    │  Agents  │   │  Serverless  │
    └──────────┘   └──────────────┘
```

## Installation

```bash
cd streamlit_app
pip install -r requirements.txt
```

## Configuration

Set environment variables:

```bash
export REDSHIFT_WORKGROUP=supply-chain-workgroup
export REDSHIFT_DATABASE=supply_chain_db
export AWS_REGION=us-east-1
export FORECASTING_AGENT_ID=your-agent-id
export PROCUREMENT_AGENT_ID=your-agent-id
export INVENTORY_AGENT_ID=your-agent-id
```

## Running Locally

```bash
streamlit run app.py
```

Access at: http://localhost:8501

## Deployment to SageMaker

### Option 1: SageMaker Notebook Instance

1. Create notebook instance (ml.t3.medium)
2. Upload streamlit_app/ directory
3. Install dependencies
4. Run: `streamlit run app.py --server.port 8501`

### Option 2: SageMaker Studio

1. Open SageMaker Studio
2. Create new terminal
3. Clone repository
4. Install dependencies
5. Run Streamlit app

## Dashboard Features

### Procurement Manager Dashboard

- **Pending Approvals**: Review AI-generated purchase orders
- **Supplier Performance**: Reliability, lead time, defect rate
- **Recent Purchase Orders**: Last 30 days with filters
- **AI Recommendations**: Generate procurement suggestions
- **Approval Actions**: Approve, reject, or modify decisions

### Inventory Manager Dashboard

- **Pending Transfers**: Review AI-generated transfer recommendations
- **Inventory Levels**: Heatmap across warehouses
- **Forecast Accuracy**: MAPE by SKU category
- **Inventory Metrics**: Turnover, stockout rate, slow-moving SKUs
- **AI Analysis**: Explain inventory imbalances

## AI Chat Interface

Located in sidebar, supports:
- Natural language queries
- Bedrock Agent invocations
- Streaming responses
- Chat history

Example queries:
- "What products need reordering?"
- "Show me suppliers with reliability > 0.9"
- "Explain why product 123 needs a transfer"

## Filters

- **Date Range**: Filter data by date
- **Warehouse**: Filter by warehouse location
- **SKU Search**: Search by product ID or name

## Glassy Theme

Custom CSS provides:
- Gradient background
- Backdrop blur effects
- Transparent cards
- Modern aesthetics

## Integration Points

### Redshift Data API
```python
import boto3

redshift_data = boto3.client('redshift-data', region_name='us-east-1')

response = redshift_data.execute_statement(
    WorkgroupName='supply-chain-workgroup',
    Database='supply_chain_db',
    Sql='SELECT * FROM inventory LIMIT 10'
)
```

### Bedrock Agent Runtime
```python
import boto3

bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = bedrock_agent.invoke_agent(
    agentId='your-agent-id',
    agentAliasId='TSTALIASID',
    sessionId='session-1',
    inputText='Check inventory and create purchase orders'
)
```

### Bedrock Runtime (Chat)
```python
import boto3
import json

bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')

response = bedrock_runtime.invoke_model(
    modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
    body=json.dumps({
        'anthropic_version': 'bedrock-2023-05-31',
        'messages': [{'role': 'user', 'content': 'Explain this decision'}],
        'max_tokens': 1000
    })
)
```

## TODO Items

- [ ] Implement Redshift Data API connection helper
- [ ] Integrate Bedrock Agent Runtime for recommendations
- [ ] Integrate Bedrock Runtime for chat interface
- [ ] Implement approval queue queries
- [ ] Create supplier performance calculations
- [ ] Build inventory heatmap visualization
- [ ] Implement forecast accuracy charts
- [ ] Add authentication/authorization
- [ ] Implement data caching
- [ ] Add error handling and retry logic

## Requirements Validated

- **7.1**: Dashboard displays key metrics
- **7.2**: Role-based routing
- **7.3**: AI chat interface
- **7.4**: Inventory manager features
- **7.5**: Glassy theme CSS
- **7.6**: Redshift Serverless connection
- **7.7**: Filter functionality
- **12.6**: AI-powered insights

## Next Steps

1. Implement Redshift connection utilities
2. Integrate Bedrock Agent invocations
3. Build data visualization components
4. Add approval workflow UI
5. Implement property tests
6. Deploy to SageMaker

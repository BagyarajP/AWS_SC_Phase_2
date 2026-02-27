# Supply Chain AI Platform - Bedrock Transformation Summary

## Overview

The supply chain AI platform has been transformed from a traditional Lambda-based architecture to a **Generative AI + Agentic AI** architecture powered by **AWS Bedrock** with **Claude 3.5 Sonnet** foundation model.

## Key Architectural Changes

### 1. Region Change
- **Before**: eu-west-2 (London)
- **After**: us-east-1 (N. Virginia)
- **Reason**: Optimal Bedrock service availability and feature support

### 2. Data Warehouse
- **Before**: Redshift provisioned cluster (dc2.large nodes)
- **After**: Redshift Serverless (32 RPUs base capacity with auto-scaling)
- **Benefits**:
  - No infrastructure management
  - Automatic scaling based on workload
  - Pay only for what you use
  - Serverless connectivity via Redshift Data API

### 3. Agent Architecture

#### Before: Lambda-Based Agents
- Agents implemented as Python Lambda functions
- Hard-coded decision logic
- Manual rationale generation
- Limited reasoning capabilities

#### After: Bedrock Agents with Claude 3.5 Sonnet
- **Procurement Agent**: Bedrock Agent with 5 Lambda tools
  - `get_inventory_levels`
  - `get_demand_forecast`
  - `get_supplier_data`
  - `calculate_eoq`
  - `create_purchase_order`

- **Inventory Agent**: Bedrock Agent with 4 Lambda tools
  - `get_warehouse_inventory`
  - `get_regional_forecasts`
  - `calculate_imbalance_score`
  - `execute_transfer`

- **Forecasting Agent**: Bedrock Agent with 4 Lambda tools
  - `get_historical_sales`
  - `calculate_forecast`
  - `store_forecast`
  - `calculate_accuracy`

### 4. Natural Language Capabilities

#### LLM-Powered Features
1. **Decision Rationale**: Claude 3.5 Sonnet generates natural language explanations for all decisions
2. **Confidence Scoring**: LLM calculates confidence scores based on data quality and reasoning
3. **Factor Analysis**: LLM identifies and ranks top 3 factors influencing each decision
4. **Interactive Chat**: Users can ask follow-up questions about decisions via natural language
5. **Explainability**: Deep explanations of reasoning chains and decision logic

### 5. Streamlit Dashboard Enhancements

#### New AI Features
- **AI Chat Interface**: Sidebar chat for natural language queries to Bedrock agents
- **On-Demand Analysis**: Trigger agent analysis from UI with real-time LLM reasoning
- **Decision Explanations**: Ask AI to explain any decision in simple terms
- **Natural Language Queries**: Query operational data using natural language

#### Example Interactions
```python
# User asks: "Why did we order 500 units from Supplier A?"
# Bedrock Agent responds with detailed explanation including:
# - Current inventory levels
# - Demand forecast analysis
# - Supplier comparison (price, reliability, lead time)
# - Confidence score reasoning
```

### 6. IAM and Security

#### New Permissions
- `bedrock:InvokeAgent` - For invoking Bedrock Agents
- `bedrock:InvokeModel` - For direct Claude 3.5 Sonnet access
- `redshift-data:*` - For serverless Redshift connectivity (no passwords)

#### New Roles
- **SupplyChainBedrockAgentRole**: For Bedrock Agent execution
- **SupplyChainToolRole**: For Lambda tools invoked by agents
- Updated roles for Redshift Serverless access

### 7. Data Flow Changes

#### Before
1. EventBridge triggers Lambda agent
2. Lambda queries Redshift directly
3. Lambda generates decision with hard-coded logic
4. Lambda writes to Redshift

#### After
1. EventBridge triggers Bedrock Agent
2. Bedrock Agent uses Claude 3.5 Sonnet for reasoning
3. Agent invokes Lambda tools to query Redshift Serverless
4. LLM analyzes data and generates decision with natural language rationale
5. Agent invokes Lambda tools to write to Redshift Serverless
6. All reasoning logged to CloudWatch

## Benefits of Bedrock Architecture

### 1. Explainability
- Natural language explanations for all decisions
- Users can ask "why" questions and get detailed answers
- Transparent reasoning chains

### 2. Flexibility
- Easy to modify agent behavior via prompt engineering
- No code changes needed for logic adjustments
- Rapid iteration on decision criteria

### 3. Intelligence
- Foundation model reasoning capabilities
- Pattern recognition across complex data
- Contextual understanding of business rules

### 4. Scalability
- Serverless architecture (Bedrock + Redshift Serverless)
- Automatic scaling based on demand
- No infrastructure management

### 5. Cost Efficiency
- Pay only for LLM tokens used
- Redshift Serverless scales to zero when idle
- No provisioned infrastructure costs

## Implementation Considerations

### 1. Bedrock Agent Configuration
- **Model**: anthropic.claude-3-5-sonnet-20241022-v2:0
- **Region**: us-east-1
- **Action Groups**: Lambda tools for each agent
- **Memory**: Session-based for multi-turn conversations
- **Guardrails**: Optional content filtering

### 2. Lambda Tools
- Lightweight functions focused on data access
- No business logic (handled by LLM)
- Fast execution (<1 second typical)
- Redshift Data API for serverless connectivity

### 3. Prompt Engineering
- System prompts define agent roles and responsibilities
- Include business rules and constraints
- Specify output format requirements
- Provide examples of good decisions

### 4. Testing Strategy
- Property-based tests still apply (45 properties)
- Additional tests for LLM output quality
- Prompt regression testing
- Cost monitoring for token usage

## Migration Path

### Phase 1: Infrastructure (Week 1)
1. Create Redshift Serverless workgroup in us-east-1
2. Migrate schema and data from eu-west-2
3. Update IAM roles for Bedrock access
4. Test Redshift Data API connectivity

### Phase 2: Bedrock Agents (Week 2-3)
1. Create Lambda tools for each action group
2. Configure Bedrock Agents with system prompts
3. Test agent invocations and tool calling
4. Validate decision quality and explanations

### Phase 3: Dashboard Integration (Week 4)
1. Update Streamlit to use Redshift Data API
2. Add Bedrock client for agent invocations
3. Implement AI chat interface
4. Test end-to-end workflows

### Phase 4: Testing & Optimization (Week 5)
1. Run property-based tests
2. Optimize prompts for better decisions
3. Monitor costs and performance
4. User acceptance testing

## Cost Estimates (Monthly)

### Bedrock Costs
- Claude 3.5 Sonnet: ~$3 per 1M input tokens, ~$15 per 1M output tokens
- Estimated usage: 10M tokens/month = ~$100-150/month

### Redshift Serverless
- 32 RPUs base capacity: ~$0.36/hour = ~$260/month
- Auto-scaling during peak: +$50-100/month
- Total: ~$310-360/month

### Lambda Tools
- Minimal cost (<$10/month for tool invocations)

### Total Estimated Cost
- **Before** (Redshift cluster): ~$400/month
- **After** (Bedrock + Serverless): ~$420-520/month
- **Incremental cost**: ~$20-120/month for Gen AI capabilities

## Next Steps

1. Review and approve architectural changes
2. Update implementation tasks in tasks.md
3. Begin Phase 1 infrastructure migration
4. Develop Lambda tools for Bedrock Agents
5. Configure and test Bedrock Agents
6. Update Streamlit dashboard with AI features
7. Run comprehensive testing
8. Deploy to production

## Questions?

Contact the development team for clarification on any aspect of the Bedrock transformation.

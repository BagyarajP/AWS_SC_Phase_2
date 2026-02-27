# Implementation Plan: Supply Chain AI Platform (Bedrock + Agentic AI)

## Overview

This implementation plan breaks down the MVP **Generative AI + Agentic AI** supply chain platform into discrete coding tasks. The platform uses AWS Bedrock (Claude 3.5 Sonnet), Bedrock Agents, Lambda tools, Redshift Serverless, Glue, SageMaker, and IAM with Python as the implementation language. All resources are deployed in **us-east-1 (N. Virginia)**. Tasks are organized to build incrementally, with testing integrated throughout.

## Architecture Summary

- **Bedrock Agents**: Three autonomous agents (Procurement, Inventory, Forecasting) powered by Claude 3.5 Sonnet
- **Lambda Tools**: Action groups for Bedrock Agents to interact with data
- **Redshift Serverless**: Data warehouse with 32 RPUs base capacity
- **Streamlit on SageMaker**: Dashboard with AI chat interface
- **Region**: us-east-1 (N. Virginia)

## Tasks

- [x] 1. Set up Redshift Serverless and synthetic data generation
  - Create Redshift Serverless workgroup in us-east-1 (32 RPUs base capacity)
  - Create SQL DDL scripts for all tables (product, warehouse, supplier, inventory, purchase_order_header, purchase_order_line, sales_order_header, sales_order_line, agent_decision, approval_queue, audit_log, demand_forecast, forecast_accuracy)
  - Write Python script to generate synthetic data for 2,000 SKUs, 500 suppliers, 3 warehouses, and 12 months of sales orders with seasonality
  - Create data loading scripts to upload CSV files to S3 (us-east-1)
  - Test Redshift Data API connectivity
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_

- [ ] 2. Implement AWS Glue ETL job for data ingestion to Redshift Serverless
  - [x] 2.1 Write Glue Python script to extract data from S3 buckets (us-east-1)
    - Implement S3 file reading logic
    - Add error handling for missing files
    - _Requirements: 6.1_
  
  - [x] 2.2 Implement data transformation logic
    - Add schema validation
    - Implement data type conversions
    - Add null value handling
    - _Requirements: 6.2_
  
  - [x] 2.3 Write property test for ETL schema conformance
    - **Property 23: ETL schema conformance**
    - **Validates: Requirements 6.2**
  
  - [x] 2.4 Implement Redshift Serverless loading logic
    - Use Redshift Data API for serverless connectivity
    - Add connection retry logic
    - _Requirements: 6.3_
  
  - [x] 2.5 Write property test for ETL data persistence
    - **Property 24: ETL data persistence**
    - **Validates: Requirements 6.3**
  
  - [x] 2.6 Add error handling and metrics tracking
    - Log errors to CloudWatch
    - Skip invalid records
    - Calculate and store record count and success rate
    - _Requirements: 6.5, 6.6_
  
  - [x] 2.7 Write property test for ETL error handling
    - **Property 25: ETL error handling**
    - **Validates: Requirements 6.5**
  
  - [x] 2.8 Write property test for ETL metrics tracking
    - **Property 26: ETL metrics tracking**
    - **Validates: Requirements 6.6**

- [x] 3. Checkpoint - Verify data ingestion
  - Ensure Glue job runs successfully and loads data into Redshift Serverless. Verify all tables are populated. Test Redshift Data API queries. Ask the user if questions arise.



- [ ] 4. Implement Forecasting Bedrock Agent with Lambda Tools
  - [x] 4.1 Create Lambda tool: get_historical_sales
    - Set up Lambda function to query Redshift Serverless via Data API
    - Retrieve 12 months of historical sales data for specified SKU
    - Return time series data in JSON format
    - Add error handling and CloudWatch logging
    - _Requirements: 3.3, 8.4_
  
  - [x] 4.2 Create Lambda tool: calculate_forecast
    - Implement Holt-Winters exponential smoothing
    - Implement ARIMA forecasting
    - Ensemble both models for final prediction
    - Calculate confidence intervals at 80% and 95% levels
    - Support 7-day and 30-day horizons
    - _Requirements: 3.3, 3.4, 3.5_
  
  - [x] 4.3 Create Lambda tool: store_forecast
    - Insert forecast records into demand_forecast table via Redshift Data API
    - Store forecast values with confidence intervals
    - Add error handling for database writes
    - _Requirements: 3.6_
  
  - [x] 4.4 Create Lambda tool: calculate_accuracy
    - Calculate MAPE for previous forecasts vs. actual demand
    - Store accuracy metrics in forecast_accuracy table
    - Return accuracy summary for LLM analysis
    - _Requirements: 3.2_
  
  - [x] 4.5 Configure Forecasting Bedrock Agent
    - Create Bedrock Agent in us-east-1
    - Use Claude 3.5 Sonnet (anthropic.claude-3-5-sonnet-20241022-v2:0)
    - Write system prompt with forecasting instructions
    - Configure action group with 4 Lambda tools
    - Set up IAM role with Bedrock and Lambda permissions
    - _Requirements: 8.1, 8.3, 8.5, 8.6_
  
  - [x] 4.6 Write property test for forecast uses historical data
    - **Property 9: Forecast uses historical data**
    - **Validates: Requirements 3.3**
  
  - [x] 4.7 Write property test for confidence interval presence
    - **Property 10: Confidence interval presence**
    - **Validates: Requirements 3.4**
  
  - [x] 4.8 Write property test for multi-horizon forecasts
    - **Property 11: Multi-horizon forecasts**
    - **Validates: Requirements 3.5**
  
  - [x] 4.9 Write property test for forecast completeness
    - **Property 8: Forecast completeness**
    - **Validates: Requirements 3.1**
  
  - [x] 4.10 Write property test for forecast persistence
    - **Property 12: Forecast persistence**
    - **Validates: Requirements 3.6**
  
  - [x] 4.11 Test Bedrock Agent end-to-end
    - Invoke agent manually via AWS Console
    - Verify LLM reasoning and tool calls
    - Check forecast quality and explanations
    - Validate CloudWatch logs
    - _Requirements: 8.6_
    - **Property 12: Forecast persistence**
    - **Validates: Requirements 3.6**
  
  - [x] 4.10 Add CloudWatch logging
    - Log execution start and completion
    - Log forecast metrics
    - Log any errors with stack traces
    - _Requirements: 8.6_
  
  - [x] 4.11 Write property test for Lambda CloudWatch logging
    - **Property 29: Lambda CloudWatch logging**
    - **Validates: Requirements 8.6**


- [ ] 5. Implement Procurement Bedrock Agent with Lambda Tools
  - [x] 5.1 Create Lambda tool: get_inventory_levels
    - Query Redshift Serverless for current inventory and reorder points
    - Support filtering by warehouse and below_reorder_point_only flag
    - Return inventory data in JSON format for LLM analysis
    - _Requirements: 1.1_
  
  - [x] 5.2 Create Lambda tool: get_demand_forecast
    - Query demand_forecast table for specified SKUs and horizon
    - Support 7-day and 30-day forecast horizons
    - Return forecast data with confidence intervals
    - _Requirements: 1.1_
  
  - [x] 5.3 Create Lambda tool: get_supplier_data
    - Query supplier table for specified product
    - Include pricing, reliability score, lead time, defect rate
    - Return supplier performance metrics for LLM evaluation
    - _Requirements: 1.6, 14.6_
  
  - [x] 5.4 Create Lambda tool: calculate_eoq
    - Implement Economic Order Quantity formula
    - Accept annual demand, order cost, holding cost as inputs
    - Return optimal order quantity
    - _Requirements: 1.2_
  
  - [x] 5.5 Create Lambda tool: create_purchase_order
    - Accept PO details, rationale, confidence score from Bedrock Agent
    - Check approval thresholds (value > £10k OR confidence < 0.7)
    - If high-risk: Insert into approval_queue
    - If low-risk: Create purchase_order_header and purchase_order_line records
    - Record decision to audit_log with LLM-generated rationale
    - _Requirements: 1.4, 1.5, 1.7, 5.1_
  
  - [x] 5.6 Configure Procurement Bedrock Agent
    - Create Bedrock Agent in us-east-1
    - Use Claude 3.5 Sonnet model
    - Write system prompt with procurement decision-making instructions
    - Configure action group with 5 Lambda tools
    - Set up IAM role with Bedrock and Lambda permissions
    - _Requirements: 8.1, 8.2, 8.5, 8.6_
  
  - [x] 5.7 Write property test for purchase order generation
    - **Property 1: Purchase order generation for low inventory**
    - **Validates: Requirements 1.1**
  
  - [x] 5.8 Write property test for supplier selection optimality
    - **Property 6: Supplier selection optimality**
    - **Validates: Requirements 1.6**
  
  - [x] 5.9 Write property test for supplier selection uses performance data
    - **Property 44: Supplier selection uses performance data**
    - **Validates: Requirements 14.6**
  
  - [x] 5.10 Write property test for decision rationale completeness
    - **Property 2: Decision rationale completeness (LLM-generated)**
    - **Validates: Requirements 1.2, 2.2, 12.1**
  
  - [x] 5.11 Write property test for confidence score validity
    - **Property 3: Confidence score validity**
    - **Validates: Requirements 1.3, 2.3**
  
  - [x] 5.12 Write property test for high-risk decision routing
    - **Property 4: High-risk decision routing**
    - **Validates: Requirements 1.4, 2.4**
  
  - [x] 5.13 Write property test for database persistence after approval
    - **Property 5: Database persistence after approval**
    - **Validates: Requirements 1.5, 2.5**
  
  - [x] 5.14 Write property test for agent decision audit logging
    - **Property 19: Agent decision audit logging**
    - **Validates: Requirements 1.7, 2.7, 5.1**
  
  - [x] 5.15 Write property test for decision factor display
    - **Property 31: Decision factor display (LLM-generated)**
    - **Validates: Requirements 12.2**
  
  - [x] 5.16 Write property test for explanation persistence
    - **Property 32: Explanation persistence (LLM-generated)**
    - **Validates: Requirements 12.3**
  
  - [x] 5.17 Test Bedrock Agent end-to-end
    - Invoke agent with low inventory scenario
    - Verify LLM reasoning and supplier selection
    - Check natural language rationale quality
    - Validate tool calls and database writes
    - _Requirements: 8.6, 12.1_


- [ ] 6. Implement Inventory Rebalancing Bedrock Agent with Lambda Tools
  - [x] 6.1 Create Lambda tool: get_warehouse_inventory
    - Query inventory table for all SKUs across all warehouses
    - Support filtering by specific SKU
    - Return current stock levels and warehouse capacities
    - _Requirements: 2.1_
  
  - [x] 6.2 Create Lambda tool: get_regional_forecasts
    - Query demand forecasts by warehouse and region
    - Support 7-day horizon for transfer planning
    - Return forecast data for LLM analysis
    - _Requirements: 2.1_
  
  - [x] 6.3 Create Lambda tool: calculate_imbalance_score
    - Calculate inventory-to-demand ratio for each warehouse
    - Identify warehouses with excess vs. shortage
    - Return imbalance metrics for LLM evaluation
    - _Requirements: 2.1_
  
  - [x] 6.4 Create Lambda tool: execute_transfer
    - Accept transfer details, rationale, confidence from Bedrock Agent
    - Check approval thresholds (quantity > 100 OR confidence < 0.75)
    - Validate warehouse capacity constraints
    - If high-risk: Insert into approval_queue
    - If low-risk: Update inventory records for source and destination
    - Record decision to audit_log with LLM-generated rationale
    - _Requirements: 2.4, 2.5, 2.6, 2.7_
  
  - [x] 6.5 Configure Inventory Bedrock Agent
    - Create Bedrock Agent in us-east-1
    - Use Claude 3.5 Sonnet model
    - Write system prompt with inventory rebalancing instructions
    - Configure action group with 4 Lambda tools
    - Set up IAM role with Bedrock and Lambda permissions
    - _Requirements: 8.1, 8.2, 8.5, 8.6_
  
  - [x] 6.6 Write property test for inventory transfer respects constraints
    - **Property 7: Inventory transfer respects constraints**
    - **Validates: Requirements 2.6**
  
  - [x] 6.7 Write property test for transfer rationale completeness
    - **Property 2: Decision rationale completeness (LLM-generated)**
    - **Validates: Requirements 2.2**
  
  - [x] 6.8 Write property test for transfer confidence score validity
    - **Property 3: Confidence score validity**
    - **Validates: Requirements 2.3**
  
  - [x] 6.9 Write property test for transfer approval routing
    - **Property 4: High-risk decision routing**
    - **Validates: Requirements 2.4**
  
  - [x] 6.10 Write property test for inventory update persistence
    - **Property 5: Database persistence after approval**
    - **Validates: Requirements 2.5**
  
  - [x] 6.11 Write property test for transfer audit logging
    - **Property 19: Agent decision audit logging**
    - **Validates: Requirements 2.7**
  
  - [x] 6.12 Test Bedrock Agent end-to-end
    - Invoke agent with imbalanced inventory scenario
    - Verify LLM reasoning and transfer recommendations
    - Check natural language rationale quality
    - Validate constraint checking and database writes
    - _Requirements: 8.6_
    - _Requirements: 2.4, 2.5_
  
  - [x] 6.7 Add audit logging
    - Record all transfer decisions to audit_log
    - _Requirements: 2.7_


- [x] 7. Checkpoint - Verify Bedrock Agent execution
  - Ensure all three Bedrock Agents run successfully. Verify LLM reasoning quality. Check tool invocations and decisions in Redshift Serverless. Test natural language explanations. Ask the user if questions arise.




- [ ] 8. Implement Streamlit dashboard with Bedrock integration
  - [x] 8.1 Create Streamlit app structure with Redshift Serverless connection
    - Set up main app file with page configuration
    - Implement Redshift Data API connection helper
    - Initialize Bedrock Runtime and Agent Runtime clients (us-east-1)
    - Add environment variable configuration
    - _Requirements: 7.1, 7.6_
  
  - [x] 8.2 Implement AI chat interface in sidebar
    - Add chat input for natural language queries
    - Integrate with Bedrock Runtime API (Claude 3.5 Sonnet)
    - Support agent invocation from chat
    - Display LLM responses with streaming
    - _Requirements: 7.3, 12.6_
  
  - [x] 8.3 Write property test for dashboard data source
    - **Property 27: Dashboard data source (Redshift Serverless)**
    - **Validates: Requirements 7.6**
  
  - [x] 8.4 Implement glassy theme CSS
    - Add custom CSS for glassy background
    - Style cards and metrics with backdrop blur
    - Add gradient background
    - Style AI chat interface
    - _Requirements: 7.5_
  
  - [x] 8.5 Create role selection and routing
    - Add sidebar role selector
    - Route to appropriate dashboard based on role
    - _Requirements: 7.2_
  
  - [x] 8.6 Implement date range and filter components
    - Add date range picker
    - Add warehouse filter dropdown
    - Add SKU filter search
    - Add natural language query option
    - _Requirements: 7.7_
  
  - [x] 8.7 Write property test for dashboard filter functionality
    - **Property 28: Dashboard filter functionality**
    - **Validates: Requirements 7.7**


- [ ] 9. Implement Procurement Manager dashboard with AI features
  - [x] 9.1 Create AI-powered insights section
    - Add "Generate Recommendations" button to invoke Procurement Bedrock Agent
    - Add "Explain Decisions" button to get LLM explanations
    - Display AI-generated insights and recommendations
    - Show agent reasoning and confidence scores
    - _Requirements: 7.3, 12.1, 12.6_
  
  - [x] 9.2 Create pending approvals section
    - Query approval_queue for Procurement_Manager role via Redshift Data API
    - Display approval cards with LLM-generated decision details
    - Show rationale, confidence score, and PO value
    - Add "Ask AI for details" button for each approval
    - _Requirements: 4.1, 4.2, 7.3_
  
  - [x] 9.3 Write property test for approval queue visibility
    - **Property 13: Approval queue visibility**
    - **Validates: Requirements 4.1**
  
  - [x] 9.4 Write property test for approval display completeness
    - **Property 14: Approval display completeness (with LLM rationale)**
    - **Validates: Requirements 4.2**
  
  - [x] 9.5 Implement approval action buttons
    - Add Approve button with Bedrock Agent invocation
    - Add Reject button with reason input
    - Add Modify button with form
    - Record actions to audit_log with LLM-generated summaries
    - _Requirements: 4.3, 4.4, 4.5_
  
  - [x] 9.6 Write property test for approval execution and logging
    - **Property 15: Approval execution and logging**
    - **Validates: Requirements 4.3**
  
  - [x] 9.7 Write property test for rejection logging
    - **Property 16: Rejection logging**
    - **Validates: Requirements 4.4**
  
  - [x] 9.8 Create recent purchase orders section
    - Query purchase_order_header for last 30 days
    - Display table with filters
    - Show metrics: total spend, average PO value
    - Add AI explanation for trends
    - _Requirements: 7.3_
  
  - [x] 9.9 Create supplier performance section
    - Query and calculate supplier metrics
    - Display supplier scorecards
    - Show reliability score, lead time, defect rate
    - Add alert badges for underperforming suppliers
    - Use Bedrock to generate performance insights
    - _Requirements: 7.3, 14.1, 14.2, 14.3, 14.4_
  
  - [x] 9.10 Write property test for supplier reliability calculation
    - **Property 40: Supplier reliability calculation**
    - **Validates: Requirements 14.1**
  
  - [x] 9.11 Write property test for supplier lead time calculation
    - **Property 41: Supplier lead time calculation**
    - **Validates: Requirements 14.2**
  
  - [x] 9.12 Write property test for supplier defect rate calculation
    - **Property 42: Supplier defect rate calculation**
    - **Validates: Requirements 14.3**
  
  - [x] 9.13 Write property test for supplier performance alerts
    - **Property 43: Supplier performance alerts**
    - **Validates: Requirements 14.5**
    - **Property 13: Approval queue visibility**
    - **Validates: Requirements 4.1**
  
  - [x] 9.3 Write property test for approval display completeness
    - **Property 14: Approval display completeness**
    - **Validates: Requirements 4.2**
  
  - [x] 9.4 Implement approval action buttons
    - Add Approve button with Lambda invocation
    - Add Reject button with reason input
    - Add Modify button with form
    - Record actions to audit_log
    - _Requirements: 4.3, 4.4, 4.5_
  
  - [x] 9.5 Write property test for approval execution and logging
    - **Property 15: Approval execution and logging**
    - **Validates: Requirements 4.3**
  
  - [x] 9.6 Write property test for rejection logging
    - **Property 16: Rejection logging**
    - **Validates: Requirements 4.4**
  
  - [x] 9.7 Create recent purchase orders section
    - Query purchase_order_header for last 30 days
    - Display table with filters
    - Show metrics: total spend, average PO value
    - _Requirements: 7.3_
  
  - [x] 9.8 Create supplier performance section
    - Query and calculate supplier metrics
    - Display supplier scorecards
    - Show reliability score, lead time, defect rate
    - Add alert badges for underperforming suppliers
    - _Requirements: 7.3, 14.1, 14.2, 14.3, 14.4_
  
  - [x] 9.9 Write property test for supplier reliability calculation
    - **Property 40: Supplier reliability calculation**
    - **Validates: Requirements 14.1**
  
  - [x] 9.10 Write property test for supplier lead time calculation
    - **Property 41: Supplier lead time calculation**
    - **Validates: Requirements 14.2**
  
  - [x] 9.11 Write property test for supplier defect rate calculation
    - **Property 42: Supplier defect rate calculation**
    - **Validates: Requirements 14.3**
  
  - [x] 9.12 Write property test for supplier performance alerts
    - **Property 43: Supplier performance alerts**
    - **Validates: Requirements 14.5**


- [ ] 10. Implement Inventory Manager dashboard with AI features
  - [x] 10.1 Create AI-powered insights section
    - Add "Generate Transfer Recommendations" button to invoke Inventory Bedrock Agent
    - Add "Explain Imbalances" button to get LLM analysis
    - Display AI-generated insights and transfer suggestions
    - Show agent reasoning and confidence scores
    - _Requirements: 7.4, 12.1, 12.6_
  
  - [x] 10.2 Create pending transfer approvals section
    - Query approval_queue for Inventory_Manager role via Redshift Data API
    - Display transfer cards with SKU, warehouses, quantity
    - Show LLM-generated rationale and confidence score
    - Add "Ask AI for details" button for each approval
    - _Requirements: 4.1, 4.2_
  
  - [x] 10.3 Write property test for role-based approval filtering
    - **Property 17: Role-based approval filtering**
    - **Validates: Requirements 4.6**
  
  - [x] 10.4 Implement transfer approval actions
    - Add Approve and Reject buttons
    - Invoke Bedrock Agent to execute approved transfers
    - Record actions to audit_log with LLM summaries
    - _Requirements: 4.3, 4.4_
  
  - [x] 10.5 Create inventory levels section
    - Query inventory by warehouse and SKU
    - Display heatmap visualization
    - Add stock status indicators (Normal/Low/Critical)
    - Use Bedrock to explain inventory patterns
    - _Requirements: 7.4_
  
  - [x] 10.6 Create inventory metrics section
    - Calculate and display inventory turnover ratio
    - Calculate and display stockout rate
    - Show slow-moving SKU count
    - Display improvement vs. baseline
    - Add AI-generated insights on metrics
    - _Requirements: 13.1, 13.2, 13.3, 13.5, 7.4_
  
  - [x] 10.7 Write property test for inventory turnover calculation
    - **Property 35: Inventory turnover calculation**
    - **Validates: Requirements 13.1**
  
  - [x] 10.8 Write property test for stockout rate calculation
    - **Property 36: Stockout rate calculation**
    - **Validates: Requirements 13.2**
  
  - [x] 10.9 Write property test for inventory improvement measurement
    - **Property 37: Inventory improvement measurement**
    - **Validates: Requirements 13.3**
  
  - [x] 10.10 Write property test for slow-moving SKU identification
    - **Property 38: Slow-moving SKU identification**
    - **Validates: Requirements 13.5**
  
  - [x] 10.11 Create forecast accuracy section
    - Query forecast_accuracy table
    - Display MAPE by SKU category
    - Show top 200 SKUs performance
    - Visualize confidence intervals
    - Add AI analysis of forecast quality
    - _Requirements: 7.4_
  
  - [x] 10.12 Add trend charts
    - Create time series charts for inventory metrics
    - Add configurable date ranges
    - Include AI-generated trend explanations
    - _Requirements: 13.6_
    - Show slow-moving SKU count
    - Display improvement vs. baseline
    - _Requirements: 13.1, 13.2, 13.3, 13.5, 7.4_
  
  - [x] 10.6 Write property test for inventory turnover calculation
    - **Property 35: Inventory turnover calculation**
    - **Validates: Requirements 13.1**
  
  - [x] 10.7 Write property test for stockout rate calculation
    - **Property 36: Stockout rate calculation**
    - **Validates: Requirements 13.2**
  
  - [x] 10.8 Write property test for inventory improvement measurement
    - **Property 37: Inventory improvement measurement**
    - **Validates: Requirements 13.3**
  
  - [x] 10.9 Write property test for slow-moving SKU identification
    - **Property 38: Slow-moving SKU identification**
    - **Validates: Requirements 13.5**
  
  - [x] 10.10 Create forecast accuracy section
    - Query forecast_accuracy table
    - Display MAPE by SKU category
    - Show top 200 SKUs performance
    - Visualize confidence intervals
    - _Requirements: 7.4_
  
  - [x] 10.11 Add trend charts
    - Create time series charts for inventory metrics
    - Add configurable date ranges
    - _Requirements: 13.6_


- [ ] 11. Implement audit log and compliance features with LLM insights
  - [x] 11.1 Create audit log query functions
    - Implement search by date range via Redshift Data API
    - Implement filter by agent (Bedrock Agent names)
    - Implement filter by user
    - Include LLM-generated rationale in results
    - _Requirements: 5.4_
  
  - [x] 11.2 Write property test for audit log search functionality
    - **Property 22: Audit log search functionality**
    - **Validates: Requirements 5.4**
  
  - [x] 11.3 Implement audit log export
    - Create CSV export function with LLM explanations
    - Add download button in dashboard
    - _Requirements: 5.5_
  
  - [x] 11.4 Add human action logging
    - Log all approvals with timestamp and user
    - Log all rejections with reason
    - Include LLM-generated summaries of actions
    - _Requirements: 5.2_
  
  - [x] 11.5 Write property test for human action audit logging
    - **Property 20: Human action audit logging**
    - **Validates: Requirements 5.2**
  
  - [x] 11.6 Add data modification logging
    - Log before and after states for all data changes
    - Use Bedrock to generate change summaries
    - _Requirements: 5.3_
  
  - [x] 11.7 Write property test for data modification audit trail
    - **Property 21: Data modification audit trail**
    - **Validates: Requirements 5.3**
  
  - [x] 11.8 Implement approval queue persistence
    - Ensure all approval requests are stored in Redshift Serverless
    - Include LLM-generated rationale
    - _Requirements: 4.7_
  
  - [x] 11.9 Write property test for approval queue persistence
    - **Property 18: Approval queue persistence**
    - **Validates: Requirements 4.7**


- [ ] 12. Implement metrics calculation and storage with AI insights
  - [x] 12.1 Create metrics calculation Lambda tools
    - Implement inventory turnover calculation
    - Implement stockout rate calculation
    - Implement supplier performance calculations
    - Make available as tools for Bedrock Agents
    - _Requirements: 13.1, 13.2, 13.3, 14.1, 14.2, 14.3_
  
  - [x] 12.2 Add metrics persistence
    - Store all calculated metrics in Redshift Serverless with timestamps
    - Include AI-generated insights on metric trends
    - _Requirements: 13.7, 14.7_
  
  - [x] 12.3 Write property test for metrics persistence
    - **Property 39: Metrics persistence**
    - **Validates: Requirements 13.7**
  
  - [x] 12.4 Write property test for supplier metrics persistence
    - **Property 45: Supplier metrics persistence**
    - **Validates: Requirements 14.7**
  
  - [x] 12.5 Implement decision accuracy tracking
    - Compare Bedrock Agent decisions to actual outcomes
    - Calculate and store accuracy metrics
    - Use insights to improve agent prompts
    - _Requirements: 12.7**
  
  - [x] 12.6 Write property test for decision accuracy tracking
    - **Property 34: Decision accuracy tracking**
    - **Validates: Requirements 12.7**


- [ ] 13. Implement IAM and authentication for Bedrock architecture
  - [x] 13.1 Configure IAM role for Bedrock Agents
    - Create SupplyChainBedrockAgentRole with Bedrock and Lambda permissions
    - Allow bedrock:InvokeModel for Claude 3.5 Sonnet
    - Allow lambda:InvokeFunction for all tool functions
    - Attach role to all three Bedrock Agents
    - _Requirements: 9.4_
  
  - [x] 13.2 Configure IAM role for Lambda tools
    - Create SupplyChainToolRole with Redshift Data API permissions
    - Allow redshift-data:ExecuteStatement and GetStatementResult
    - Allow CloudWatch logging
    - Attach role to all Lambda tool functions
    - _Requirements: 9.4_
  
  - [x] 13.3 Configure IAM role for Glue job
    - Create SupplyChainGlueRole with S3 and Redshift Serverless permissions
    - Update for us-east-1 region
    - Attach role to Glue job
    - _Requirements: 9.4_
  
  - [x] 13.4 Configure IAM role for SageMaker notebook
    - Create SupplyChainStreamlitRole with Redshift, Bedrock, and Lambda permissions
    - Allow bedrock:InvokeAgent and bedrock:InvokeModel
    - Allow redshift-data API access
    - Attach role to SageMaker notebook instance
    - _Requirements: 9.4_
  
  - [x] 13.5 Add authentication logging
    - Log all authentication attempts to CloudWatch
    - Log Bedrock Agent invocations
    - _Requirements: 9.7_
  
  - [x] 13.6 Write property test for authentication logging
    - **Property 30: Authentication logging**
    - **Validates: Requirements 9.7**


- [ ] 14. Implement EventBridge scheduling for Bedrock Agents
  - [x] 14.1 Create EventBridge rule for Forecasting Bedrock Agent
    - Schedule daily trigger at 1:00 AM UTC
    - Target Forecasting Bedrock Agent (not Lambda directly)
    - Configure in us-east-1 region
    - _Requirements: 3.7, 8.3_
  
  - [x] 14.2 Create EventBridge rule for Procurement Bedrock Agent
    - Schedule daily trigger at 2:00 AM UTC
    - Target Procurement Bedrock Agent
    - Configure in us-east-1 region
    - _Requirements: 8.1, 8.2_
  
  - [x] 14.3 Create EventBridge rule for Inventory Bedrock Agent
    - Schedule daily trigger at 3:00 AM UTC
    - Target Inventory Bedrock Agent
    - Configure in us-east-1 region
    - _Requirements: 8.2_


- [ ] 15. Final integration and testing with Bedrock
  - [x] 15.1 Deploy all Lambda tool functions to AWS
    - Package Lambda tools with dependencies
    - Upload to AWS Lambda in us-east-1
    - Configure environment variables for Redshift Serverless
    - Test manual invocation of each tool
  
  - [x] 15.2 Deploy Bedrock Agents
    - Create and configure all three Bedrock Agents in us-east-1
    - Link action groups to Lambda tools
    - Test agent invocations and tool calling
    - Validate LLM reasoning quality
  
  - [x] 15.3 Deploy Streamlit app to SageMaker
    - Create SageMaker notebook instance in us-east-1
    - Upload Streamlit app code with Bedrock integration
    - Configure Redshift Serverless connection via Data API
    - Configure Bedrock client for agent invocations
    - Test dashboard access and AI features
  
  - [x] 15.4 Run end-to-end integration tests
    - Trigger Glue job to load synthetic data into Redshift Serverless
    - Trigger all Bedrock Agents manually
    - Verify LLM-generated decisions appear in dashboard
    - Test approval workflow with AI explanations
    - Verify audit log entries with LLM rationale
    - Test AI chat interface
  
  - [x] 15.5 Run all property-based tests
    - Execute all 45 property tests with 100+ iterations each
    - Verify all properties pass
    - Test LLM output quality and consistency
    - Document any failures
  
  - [x] 15.6 Validate Bedrock Agent performance
    - Test agent response times
    - Monitor token usage and costs
    - Validate reasoning quality across multiple scenarios
    - Test edge cases and error handling
    - Trigger all Lambda agents manually
    - Verify decisions appear in dashboard
    - Test approval workflow
    - Verify audit log entries
  
  - [x] 15.4 Run all property-based tests
    - Execute all 45 property tests with 100+ iterations each
    - Verify all properties pass
    - Document any failures


- [x] 16. Final checkpoint - Complete Bedrock system verification
  - Ensure all Bedrock Agents are deployed and working in us-east-1. Verify Redshift Serverless connectivity. Test LLM reasoning quality and natural language explanations. Verify end-to-end workflows with AI features. Monitor token usage and costs. Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property-based tests and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (45 total)
- Unit tests validate specific examples and edge cases
- All Lambda tool functions use Python 3.9+
- All database operations use Redshift Data API (serverless, no connection pooling)
- Bedrock Agents use Claude 3.5 Sonnet (anthropic.claude-3-5-sonnet-20241022-v2:0)
- All resources deployed in us-east-1 (N. Virginia)
- Streamlit app uses plotly for visualizations and boto3 for Bedrock integration
- Testing uses pytest and hypothesis frameworks
- LLM output quality testing included for natural language rationale and explanations

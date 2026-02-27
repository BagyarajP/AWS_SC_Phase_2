"""
Forecasting Agent Lambda Router
Routes Bedrock Agent tool calls to appropriate tool implementations
"""

import json
import logging
import os
from typing import Dict, Any

# Import tool functions
from tools.get_historical_sales import lambda_handler as get_historical_sales_handler
from tools.calculate_forecast import lambda_handler as calculate_forecast_handler
from tools.store_forecast import lambda_handler as store_forecast_handler
from tools.calculate_accuracy import lambda_handler as calculate_accuracy_handler

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Tool routing map
TOOL_HANDLERS = {
    'getHistoricalSales': get_historical_sales_handler,
    'calculateForecast': calculate_forecast_handler,
    'storeForecast': store_forecast_handler,
    'calculateAccuracy': calculate_accuracy_handler
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Bedrock Agent tool invocations
    
    Args:
        event: Bedrock Agent event containing tool invocation details
        context: Lambda context object
        
    Returns:
        Response in Bedrock Agent format
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract tool information from Bedrock Agent event
        agent = event.get('agent', '')
        action_group = event.get('actionGroup', '')
        api_path = event.get('apiPath', '')
        http_method = event.get('httpMethod', '')
        parameters = event.get('parameters', [])
        request_body = event.get('requestBody', {})
        
        logger.info(f"Agent: {agent}, Action Group: {action_group}, API Path: {api_path}")
        
        # Determine which tool to invoke based on API path
        tool_name = None
        if api_path == '/get_historical_sales':
            tool_name = 'getHistoricalSales'
        elif api_path == '/calculate_forecast':
            tool_name = 'calculateForecast'
        elif api_path == '/store_forecast':
            tool_name = 'storeForecast'
        elif api_path == '/calculate_accuracy':
            tool_name = 'calculateAccuracy'
        else:
            return create_error_response(f"Unknown API path: {api_path}")
        
        # Get tool handler
        tool_handler = TOOL_HANDLERS.get(tool_name)
        if not tool_handler:
            return create_error_response(f"No handler found for tool: {tool_name}")
        
        # Parse request body
        if request_body and 'content' in request_body:
            content = request_body['content']
            if isinstance(content, dict) and 'application/json' in content:
                tool_input = json.loads(content['application/json'])
            else:
                tool_input = {}
        else:
            tool_input = {}
        
        # Add parameters to tool input
        for param in parameters:
            param_name = param.get('name')
            param_value = param.get('value')
            if param_name and param_value:
                tool_input[param_name] = param_value
        
        logger.info(f"Invoking tool {tool_name} with input: {json.dumps(tool_input)}")
        
        # Invoke tool handler
        tool_response = tool_handler(tool_input, context)
        
        logger.info(f"Tool response: {json.dumps(tool_response)}")
        
        # Format response for Bedrock Agent
        return create_success_response(tool_response)
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return create_error_response(str(e))


def create_success_response(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a successful response in Bedrock Agent format
    
    Args:
        body: Response body to return
        
    Returns:
        Formatted response for Bedrock Agent
    """
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': 'forecasting-tools',
            'apiPath': '',
            'httpMethod': 'POST',
            'httpStatusCode': 200,
            'responseBody': {
                'application/json': {
                    'body': json.dumps(body)
                }
            }
        }
    }


def create_error_response(error_message: str) -> Dict[str, Any]:
    """
    Create an error response in Bedrock Agent format
    
    Args:
        error_message: Error message to return
        
    Returns:
        Formatted error response for Bedrock Agent
    """
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': 'forecasting-tools',
            'apiPath': '',
            'httpMethod': 'POST',
            'httpStatusCode': 500,
            'responseBody': {
                'application/json': {
                    'body': json.dumps({
                        'error': error_message
                    })
                }
            }
        }
    }

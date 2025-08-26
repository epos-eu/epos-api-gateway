import os
import requests
from flask import request, Response
import logging

logger = logging.getLogger(__name__)

def submit_feedback():
    try:
        # Get configuration
        feedback_destination = os.getenv("FEEDBACK_DESTINATION_URL")
        feedback_token = os.getenv("FEEDBACK_TOKEN")

        # Validate environment variables
        if not feedback_destination:
            logger.error("FEEDBACK_DESTINATION_URL enviroment variable is not set")
            return Response('{"error": "Feedback service not configured, "}', status=500, content_type='application/json')
        
        if not feedback_token:
            logger.error("FEEDBACK_TOKEN environment variable is not set")
            return Response('{"error": "Feedback authentication not configured"}', status=500, content_type='application/json')
        # Validate request
        if not request.is_json:
            return Response('{"error": "Request must be JSON"}', status=400, content_type='application/json')

        body = request.get_json()
        
        # Validate required fields (optional but recommended)
        if not body or 'title' not in body:
            return Response('{"error": "Missing title field"}', status=400, content_type='application/json')

        # Prepare headers
        headers = {
            "PRIVATE-TOKEN": feedback_token,
            "Content-Type": "application/json"
        }

        logger.info(f"Submitting feedback to: {feedback_destination}")
        
  
        feedback_request = requests.post(
            feedback_destination, 
            headers=headers, 
            json=body,
        )

        return Response(
            feedback_request.content, 
            feedback_request.status_code, 
            content_type=feedback_request.headers.get("Content-Type", "application/json")
        )
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to feedback service")
        return Response('{"error": "Cannot connect to feedback service"}', status=503, content_type='application/json')
    except requests.exceptions.RequestException as e:
        logger.error(f"Feedback request failed: {str(e)}")
        return Response('{"error": "Failed to submit feedback"}', status=500, content_type='application/json')
    except Exception as e:
        logger.error(f"Unexpected error in submit_feedback: {str(e)}")
        return Response('{"error": "Internal server error"}', status=500, content_type='application/json')
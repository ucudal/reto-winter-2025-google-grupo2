import functions_framework
import json
import os
import uuid
from google.cloud.dialogflowcx_v3beta1.services import sessions
from google.cloud.dialogflowcx_v3beta1.types import session

# Set your project configuration as environment variables in Cloud Functions
PROJECT_ID = os.environ.get('PROJECT_ID')
LOCATION_ID = os.environ.get('LOCATION_ID')
AGENT_ID = os.environ.get('AGENT_ID')

@functions_framework.http
def dialogflow_proxy_webhook(request):
    """
    HTTP Cloud Function that acts as a proxy for a Dialogflow CX agent.
    It receives a message, calls the Detect Intent API, and returns the agent's response.
    """
    # 1. Receive the user's message from the incoming webhook request
    request_json = request.get_json(silent=True)
    if not request_json or 'message' not in request_json:
        return json.dumps({"error": "No 'message' field found in request."}), 400
        
    user_message = request_json['message']

    # 2. Get a session ID (critical for maintaining conversational context)
    # You can get this from the request, a cookie, or generate a new one.
    # For this example, we'll generate a UUID for each new session.
    session_id = request_json.get('session_id', str(uuid.uuid4()))

    # 3. Call the Dialogflow CX Detect Intent API
    try:
        # The API endpoint is determined by the agent's location
        api_endpoint = f"{LOCATION_ID}-dialogflow.googleapis.com:443"
        client_options = {"api_endpoint": api_endpoint}
        client = sessions.SessionsClient(client_options=client_options)
        
        session_path = client.session_path(
            project=PROJECT_ID,
            location=LOCATION_ID,
            agent=AGENT_ID,
            session=session_id
        )

        query_input = session.QueryInput(text=session.TextInput(text=user_message), language_code="en")

        request = session.DetectIntentRequest(
            session=session_path,
            query_input=query_input
        )
        
        response = client.detect_intent(request)
        
        # 4. Extract the agent's fulfillment text
        fulfillment_text = response.query_result.response_messages[0].text.text[0]
        
    except Exception as e:
        return json.dumps({"error": f"Failed to call Dialogflow API: {str(e)}"}), 500
        
    # 5. Return the agent's response to the user's webhook caller
    final_response = {
        "agent_response": fulfillment_text,
        "session_id": session_id
    }
    
    return json.dumps(final_response), 200
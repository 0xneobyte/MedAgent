from langgraph.graph import StateGraph
from typing import Dict, Any, TypedDict, List
from app.agents.receptionist import receptionist_agent
from app.agents.appointment import appointment_agent
from app.agents.call_center import call_center_agent
from app.agents.content_management import content_management_agent
from app.agents.notification import notification_agent

# Define a TypedDict for our state schema
class WorkflowState(TypedDict):
    transcript: str
    intent: str
    patient_id: str
    response: str
    appointment_details: Dict[str, Any]
    conversation_in_progress: bool
    original_intent: str
    appointment_context: Dict[str, Any]

# Wrap the receptionist agent to preserve intent
def receptionist_agent_wrapper(state):
    """
    Wrapper around receptionist_agent that preserves intent for ongoing conversations
    """
    # Print received state for debugging
    print(f"DEBUG WORKFLOW: Processing state with transcript: '{state.get('transcript', '')}'")
    print(f"DEBUG WORKFLOW: Initial state: {state}")
    
    # Check if we're in an ongoing appointment conversation
    if state.get("conversation_in_progress") and state.get("original_intent"):
        # If we're in a conversation, preserve the original intent
        print(f"DEBUG WORKFLOW: Preserving original intent: {state.get('original_intent')}")
        
        # First let the receptionist do its job
        updated_state = receptionist_agent(state)
        
        # Then override the intent with the original intent
        # UNLESS it's a cancellation or rescheduling update from the appointment agent
        if updated_state.get("intent") not in ["cancel_appointment", "reschedule_appointment"]:
            updated_state["intent"] = state.get("original_intent")
            print(f"DEBUG WORKFLOW: Overriding intent to: {updated_state['intent']}")
        else:
            print(f"DEBUG WORKFLOW: Detected special intent {updated_state.get('intent')}, not overriding")
        
        return updated_state
    else:
        # Not in a conversation yet, let receptionist process normally
        updated_state = receptionist_agent(state)
        
        # If this is a new appointment intent, mark the conversation as in progress
        if updated_state.get("intent") in ["schedule_appointment", "cancel_appointment", "reschedule_appointment"]:
            print(f"DEBUG WORKFLOW: New {updated_state.get('intent')} conversation detected, marking as in progress")
            updated_state["conversation_in_progress"] = True
            updated_state["original_intent"] = updated_state.get("intent")
        
        return updated_state

# Define the state flow for our agents with state_schema
workflow_builder = StateGraph(state_schema=WorkflowState)

# Add nodes for each agent - use our wrapper for receptionist
workflow_builder.add_node("receptionist", receptionist_agent_wrapper)
workflow_builder.add_node("appointment", appointment_agent)
workflow_builder.add_node("call_center", call_center_agent)
workflow_builder.add_node("content_management", content_management_agent)
workflow_builder.add_node("notification", notification_agent)

# Define the edges between agents
# The receptionist is the entry point and routes based on intent
def route_by_intent(state):
    intent = state.get("intent", "")
    
    # For debugging
    print(f"DEBUG WORKFLOW: Routing based on intent: {intent}")
    
    if intent in ["schedule_appointment", "book_appointment", "cancel_appointment", "reschedule_appointment"]:
        print(f"DEBUG WORKFLOW: Routing to appointment agent for {intent}")
        return "appointment"
    elif intent == "general_inquiry":
        return "call_center"
    else:
        # Default to call center for unknown intents
        return "call_center"

# Set up the routing from receptionist
workflow_builder.add_conditional_edges(
    "receptionist",
    route_by_intent,
    {
        "appointment": "appointment",
        "call_center": "call_center",
    }
)

# After appointment handling, route to notification agent
def prepare_for_notification(state):
    print(f"DEBUG WORKFLOW: Preparing state for notification agent")
    print(f"DEBUG WORKFLOW: Intent for notification: {state.get('intent')}")
    if "cancellation_details" in state:
        print(f"DEBUG WORKFLOW: Found cancellation details: {state['cancellation_details']}")
    return state

# Use standard add_edge without transform parameter
workflow_builder.add_edge("appointment", "notification")

# Add a conditional edge from notification to content management
def after_notification(state):
    print(f"DEBUG WORKFLOW: After notification agent, state contains: {list(state.keys())}")
    print(f"DEBUG WORKFLOW: Intent after notification: {state.get('intent', 'None')}")
    if "cancellation_details" in state:
        print(f"DEBUG WORKFLOW: Has cancellation details: {state['cancellation_details']}")
    return "content_management"

workflow_builder.add_conditional_edges(
    "notification",
    after_notification,
    {
        "content_management": "content_management",
    }
)

# All other responses should go through content management for validation
workflow_builder.add_edge("call_center", "content_management")

# Set the entry point to receptionist
workflow_builder.set_entry_point("receptionist")

# Compile the graph
workflow = workflow_builder.compile()

# Wrapper function for the workflow to initialize state properly
def process_workflow(input_state):
    """
    Process the workflow with proper state initialization
    """
    # Initialize conversation tracking if not present
    if "conversation_in_progress" not in input_state:
        input_state["conversation_in_progress"] = False
    if "original_intent" not in input_state:
        input_state["original_intent"] = ""
    if "appointment_context" not in input_state:
        input_state["appointment_context"] = {}
    
    # Store original state for post-processing
    original_intent = input_state.get("intent")
    
    # Check for cancellation details in input state
    has_cancellation_direct = "cancellation_details" in input_state
    has_cancellation_context = "appointment_context" in input_state and "cancellation_details" in input_state["appointment_context"]
    
    # Store original cancellation details if they exist
    cancellation_details = None
    if has_cancellation_direct:
        cancellation_details = input_state["cancellation_details"]
        print("DEBUG WORKFLOW: Found cancellation details directly in input state")
    elif has_cancellation_context:
        cancellation_details = input_state["appointment_context"]["cancellation_details"]
        print("DEBUG WORKFLOW: Found cancellation details in appointment_context")
    
    # Run the workflow
    print("DEBUG WORKFLOW: Running workflow with input state keys:", list(input_state.keys()))
    final_state = workflow.invoke(input_state)
    print("DEBUG WORKFLOW: Workflow returned final state keys:", list(final_state.keys()))
    
    # Check for cancellation intent and details in the final state
    if final_state.get("intent") == "cancel_appointment":
        print("DEBUG WORKFLOW: Final state has cancel_appointment intent")
        
        # Ensure cancellation details are in the final state
        if "cancellation_details" not in final_state and cancellation_details:
            print("DEBUG WORKFLOW: Restoring cancellation details to final state")
            final_state["cancellation_details"] = cancellation_details
        
        # Also check if cancellation details are in the appointment_context
        if "appointment_context" in final_state and "cancellation_details" in final_state["appointment_context"]:
            print("DEBUG WORKFLOW: Found cancellation details in final appointment_context")
            
            # Make sure they're also in the root state
            if "cancellation_details" not in final_state:
                final_state["cancellation_details"] = final_state["appointment_context"]["cancellation_details"]
                print("DEBUG WORKFLOW: Copied cancellation details from context to root state")
    
    # Ensure appointment_context is preserved in the final state
    if "appointment_context" in input_state and "appointment_context" not in final_state:
        final_state["appointment_context"] = input_state["appointment_context"]
        
    # Important: If the appointment agent created or updated the appointment_context, make sure it's in the final state
    if isinstance(final_state, dict) and "appointment_context" not in final_state and any(key == "appointment_context" for key in final_state):
        for key in final_state:
            if key == "appointment_context":
                final_state["appointment_context"] = final_state[key]
                break
    
    return final_state 
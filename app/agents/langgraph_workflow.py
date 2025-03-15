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
        updated_state["intent"] = state.get("original_intent")
        print(f"DEBUG WORKFLOW: Overriding intent to: {updated_state['intent']}")
        
        return updated_state
    else:
        # Not in a conversation yet, let receptionist process normally
        updated_state = receptionist_agent(state)
        
        # If this is a new appointment intent, mark the conversation as in progress
        if "appointment" in updated_state.get("intent", ""):
            print(f"DEBUG WORKFLOW: Setting conversation_in_progress=True for appointment intent")
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
    
    if "appointment" in intent:
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
workflow_builder.add_edge("appointment", "notification")

# All responses should go through content management for validation
workflow_builder.add_edge("notification", "content_management")
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
    
    # Run the workflow
    final_state = workflow.invoke(input_state)
    
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
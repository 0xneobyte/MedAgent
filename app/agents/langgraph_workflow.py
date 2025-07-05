import logging
from langgraph.graph import StateGraph
from typing import Dict, Any, TypedDict, List
from app.agents.receptionist import receptionist_agent
from app.agents.appointment import appointment_agent
from app.agents.call_center import call_center_agent
from app.agents.content_management import content_management_agent
from app.agents.notification import notification_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    # Get the appointment context to check current state
    appointment_context = state.get("appointment_context", {})
    current_appt_state = appointment_context.get("state", "initial")
    
    # Check if we're in an ongoing appointment conversation
    if state.get("conversation_in_progress") and state.get("original_intent"):
        # If we're in a conversation, preserve the original intent
        logger.info(f"Workflow: Continuing conversation with preserved intent: {state.get('original_intent')}")
        
        # First let the receptionist do its job
        updated_state = receptionist_agent(state)
        
        # Check for explicit cancellation/rescheduling keywords in the transcript
        transcript = state.get("transcript", "").lower()
        has_cancel = "cancel" in transcript
        has_reschedule = "reschedule" in transcript or "change appointment" in transcript
        
        # Determine if we should keep the original intent or allow a new one
        if has_cancel and updated_state.get("intent") != "cancel_appointment":
            # Override with cancellation intent
            updated_state["intent"] = "cancel_appointment"
            logger.info(f"Workflow: Intent overridden to cancellation based on user input")
        elif has_reschedule and updated_state.get("intent") != "reschedule_appointment":
            # Override with reschedule intent
            updated_state["intent"] = "reschedule_appointment"
            logger.info(f"Workflow: Intent overridden to reschedule based on user input")
        # If we're already in a cancellation or rescheduling flow, maintain that intent
        elif "cancell" in current_appt_state:
            updated_state["intent"] = "cancel_appointment"
        elif "reschedul" in current_appt_state:
            updated_state["intent"] = "reschedule_appointment" 
        # Otherwise maintain the original intent if the new one isn't a special intent
        elif updated_state.get("intent") not in ["cancel_appointment", "reschedule_appointment"]:
            updated_state["intent"] = state.get("original_intent")
        
        return updated_state
    else:
        # Not in a conversation yet, let receptionist process normally
        updated_state = receptionist_agent(state)
        
        # Check for keywords in the transcript
        transcript = state.get("transcript", "").lower()
        has_cancel = "cancel" in transcript
        has_reschedule = "reschedule" in transcript or "change appointment" in transcript
        
        # If keywords are present but intent doesn't match, override it
        if has_cancel and updated_state.get("intent") != "cancel_appointment":
            updated_state["intent"] = "cancel_appointment"
        elif has_reschedule and updated_state.get("intent") != "reschedule_appointment":
            updated_state["intent"] = "reschedule_appointment"
        
        # If this is a new appointment intent, mark the conversation as in progress
        if updated_state.get("intent") in ["schedule_appointment", "cancel_appointment", "reschedule_appointment"]:
            logger.info(f"Workflow: New {updated_state.get('intent')} conversation started")
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
    
    logger.info(f"Workflow Router: Intent '{intent}' detected")
    
    # Check if we need to switch context from appointment to general conversation
    if state.get("switch_context", False):
        logger.info(f"Context switch detected - routing to call center")
        # Clear the switch_context flag so it doesn't persist
        state["switch_context"] = False
        return "call_center"
    
    # Check if we have a completed operation and a new different intent
    if "appointment_context" in state:
        context = state.get("appointment_context", {})
        current_state = context.get("state", "")
        
        # Check if we just completed an operation but now have a different intent
        completed_states = ["booking_confirmed", "cancellation_confirmed", "reschedule_confirmed"]
        
        if current_state in completed_states:
            # If we've completed an operation and have a new appointment-related intent,
            # route directly to appointment handling
            if intent in ["schedule_appointment", "book_appointment", "cancel_appointment", "reschedule_appointment"]:
                logger.info(f"Operation completed - routing new '{intent}' to appointment agent")
                return "appointment"
    
    # Standard intent routing
    if intent in ["schedule_appointment", "book_appointment", "cancel_appointment", "reschedule_appointment"]:
        logger.info(f"Routing to Appointment Agent")
        return "appointment"
    else:
        # Route all other intents to call center (general_inquiry, health_question, other, unknown, etc.)
        logger.info(f"Routing to Call Center Agent")
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

# After appointment handling, conditionally route to notification agent
def should_send_notification(state):
    """Determine if we should route to notification agent"""
    # Check if we've already sent a notification for this operation
    if state.get("notification_sent", False):
        logger.info(f"Notification already sent - skipping to content management")
        return "content_management"
    
    # Direct flag from appointment agent
    if state.get("needs_notification", False):
        logger.info(f"Notification explicitly requested - routing to notification agent")
        return "notification"
    
    # Check for fresh appointment details (new booking)
    has_new_appointment = (
        state.get("intent") in ["schedule_appointment", "book_appointment"] and 
        "appointment_details" in state
    )
    
    # Check for fresh cancellation details
    has_cancellation = (
        state.get("intent") == "cancel_appointment" and 
        (
            "cancellation_details" in state or 
            ("appointment_context" in state and "cancellation_details" in state["appointment_context"])
        )
    )
    
    # Check for fresh rescheduling details
    has_reschedule = (
        state.get("intent") == "reschedule_appointment" and 
        (
            "reschedule_details" in state or
            ("appointment_context" in state and "reschedule_details" in state["appointment_context"])
        )
    )
    
    # Check for operation completion flags
    operation_just_completed = False
    if "appointment_context" in state:
        context = state["appointment_context"]
        if context.get("state") in ["booking_confirmed", "cancellation_confirmed", "reschedule_confirmed"]:
            # Only count as just completed if notification hasn't been sent
            if (context.get("state") == "booking_confirmed" and not context.get("booking_notification_sent", False)) or \
               (context.get("state") == "cancellation_confirmed" and not context.get("cancellation_notification_sent", False)) or \
               (context.get("state") == "reschedule_confirmed" and not context.get("reschedule_notification_sent", False)):
                operation_just_completed = True
    
    needs_notification = has_new_appointment or has_cancellation or has_reschedule or operation_just_completed
    
    if needs_notification:
        logger.info(f"Notification needed - routing to notification agent")
        return "notification"
    else:
        logger.info(f"No notification needed - proceeding to content management")
        return "content_management"

# Replace direct edge with conditional routing
# workflow_builder.add_edge("appointment", "notification")
workflow_builder.add_conditional_edges(
    "appointment",
    should_send_notification,
    {
        "notification": "notification",
        "content_management": "content_management",
    }
)

# Add a conditional edge from notification to content management
def after_notification(state):
    logger.info(f"Notification completed - routing to content management for final validation")
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
    elif has_cancellation_context:
        cancellation_details = input_state["appointment_context"]["cancellation_details"]
    
    # Run the workflow
    logger.info(f"LangGraph workflow execution started")
    final_state = workflow.invoke(input_state)
    logger.info(f"LangGraph workflow execution completed")
    
    # Check for cancellation intent and details in the final state
    if final_state.get("intent") == "cancel_appointment":        
        # Ensure cancellation details are in the final state
        if "cancellation_details" not in final_state and cancellation_details:
            final_state["cancellation_details"] = cancellation_details
        
        # Also check if cancellation details are in the appointment_context
        if "appointment_context" in final_state and "cancellation_details" in final_state["appointment_context"]:
            # Make sure they're also in the root state
            if "cancellation_details" not in final_state:
                final_state["cancellation_details"] = final_state["appointment_context"]["cancellation_details"]
    
    # Check if we need to reset the conversation state due to a context switch
    if final_state.get("switch_context", False):
        logger.info(f"Context switch detected - resetting conversation tracking")
        final_state["conversation_in_progress"] = False
        final_state["original_intent"] = ""
        
        # Keep only minimal appointment context
        if "appointment_context" in final_state and isinstance(final_state["appointment_context"], dict):
            # Preserve notification flags and other critical info
            notification_flags = {
                "booking_notification_sent": final_state["appointment_context"].get("booking_notification_sent", False),
                "cancellation_notification_sent": final_state["appointment_context"].get("cancellation_notification_sent", False),
                "reschedule_notification_sent": final_state["appointment_context"].get("reschedule_notification_sent", False)
            }
            
            # Preserve only the completion flags and last action
            minimal_context = {
                "state": final_state["appointment_context"].get("state", "initial"),
                "booking_complete": final_state["appointment_context"].get("booking_complete", False),
                "cancellation_complete": final_state["appointment_context"].get("cancellation_complete", False),
                "reschedule_complete": final_state["appointment_context"].get("reschedule_complete", False),
                "last_completed_action": final_state["appointment_context"].get("last_completed_action", "")
            }
            
            # Add notification flags back in
            minimal_context.update(notification_flags)
            
            final_state["appointment_context"] = minimal_context
        
        # Remove the switch_context flag so it doesn't trigger again
        final_state.pop("switch_context", None)
    
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
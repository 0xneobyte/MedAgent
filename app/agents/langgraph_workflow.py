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

# Define the state flow for our agents
workflow = StateGraph(state_schema=WorkflowState)

# Add nodes for each agent
workflow.add_node("receptionist", receptionist_agent)
workflow.add_node("appointment", appointment_agent)
workflow.add_node("call_center", call_center_agent)
workflow.add_node("content_management", content_management_agent)
workflow.add_node("notification", notification_agent)

# Define the edges between agents
# The receptionist is the entry point and routes based on intent
def route_by_intent(state):
    intent = state.get("intent", "")
    
    if "appointment" in intent:
        return "appointment"
    elif intent == "general_inquiry":
        return "call_center"
    else:
        # Default to call center for unknown intents
        return "call_center"

# Set up the routing from receptionist
workflow.add_conditional_edges(
    "receptionist",
    route_by_intent,
    {
        "appointment": "appointment",
        "call_center": "call_center",
    }
)

# After appointment handling, route to notification agent
workflow.add_edge("appointment", "notification")

# All responses should go through content management for validation
workflow.add_edge("notification", "content_management")
workflow.add_edge("call_center", "content_management")

# Set the entry point to receptionist
workflow.set_entry_point("receptionist")

# Compile the graph
workflow.compile() 
import os
from openai import OpenAI
from langfuse.client import Langfuse
import datetime
import json

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Langfuse for logging
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)

# For demo purposes, we'll use a simple in-memory database
# In a real application, this would be a MongoDB database
APPOINTMENTS = [
    {
        "id": "appt1",
        "patient_id": "demo_patient",
        "date": "2023-07-15",
        "time": "14:00",
        "doctor": "Dr. Smith",
        "reason": "Annual checkup"
    }
]

def get_available_slots(date):
    """
    Get available appointment slots for a given date
    
    Args:
        date: The date to check for available slots
    
    Returns:
        list: A list of available time slots
    """
    # In a real system, this would query a database
    # For this demo, we'll return fixed slots
    all_slots = ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00"]
    
    # Remove slots that are already booked
    booked_slots = [appt["time"] for appt in APPOINTMENTS if appt["date"] == date]
    available_slots = [slot for slot in all_slots if slot not in booked_slots]
    
    return available_slots

def book_appointment(patient_id, date, time, reason):
    """
    Book a new appointment
    
    Args:
        patient_id: The ID of the patient
        date: The date for the appointment
        time: The time for the appointment
        reason: The reason for the appointment
    
    Returns:
        dict: The newly created appointment
    """
    # Check if slot is available
    available_slots = get_available_slots(date)
    if time not in available_slots:
        return None
    
    # Create a new appointment
    new_appointment = {
        "id": f"appt{len(APPOINTMENTS) + 1}",
        "patient_id": patient_id,
        "date": date,
        "time": time,
        "doctor": "Dr. Smith",  # Simplified for demo
        "reason": reason
    }
    
    # Add to our in-memory database
    APPOINTMENTS.append(new_appointment)
    
    return new_appointment

def cancel_appointment(appointment_id):
    """
    Cancel an existing appointment
    
    Args:
        appointment_id: The ID of the appointment to cancel
    
    Returns:
        bool: True if the appointment was canceled, False otherwise
    """
    global APPOINTMENTS
    
    # Find and remove the appointment
    for i, appt in enumerate(APPOINTMENTS):
        if appt["id"] == appointment_id:
            APPOINTMENTS.pop(i)
            return True
    
    return False

def find_appointments(patient_id):
    """
    Find all appointments for a patient
    
    Args:
        patient_id: The ID of the patient
    
    Returns:
        list: A list of appointments for the patient
    """
    return [appt for appt in APPOINTMENTS if appt["patient_id"] == patient_id]

def appointment_agent(state):
    """
    The main Appointment Agent function for LangGraph
    
    Args:
        state: The current state object from LangGraph
    
    Returns:
        dict: Updated state with appointment information and response
    """
    # Create a trace in Langfuse
    trace = langfuse.trace(
        name="appointment_agent",
        metadata={
            "transcript": state.get("transcript", ""),
            "intent": state.get("intent", "unknown")
        }
    )
    
    try:
        # Extract relevant information from the state
        transcript = state.get("transcript", "")
        intent = state.get("intent", "")
        patient_id = state.get("patient_id", "demo_patient")
        
        # Only process if the intent is appointment-related
        if "appointment" not in intent:
            state["response"] = "I'm not sure I understand what you need. Are you trying to schedule an appointment?"
            return state
        
        system_prompt = """
        You are an AI appointment assistant for a healthcare clinic. Extract relevant appointment details
        from the patient's request. If the patient wants to schedule an appointment, extract the preferred
        date, time, and reason. If they want to cancel, identify which appointment they're referring to.
        
        For scheduling, provide this JSON format:
        {"action": "schedule", "date": "YYYY-MM-DD", "time": "HH:MM", "reason": "reason for visit"}
        
        For cancellation, provide this JSON format:
        {"action": "cancel", "appointment_id": "ID or description of the appointment"}
        
        For rescheduling, provide this JSON format:
        {"action": "reschedule", "appointment_id": "ID or description", "new_date": "YYYY-MM-DD", "new_time": "HH:MM"}
        
        If information is missing, provide this format:
        {"action": "incomplete", "missing": ["list of missing fields"]}
        
        Only output valid JSON without additional text.
        """
        
        # Create a Langfuse span for timing
        with trace.span(name="gpt4_appointment_extraction") as span:
            # Extract appointment details using GPT-4o
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript}
                ],
                temperature=0.1
            )
            
            try:
                # Parse the JSON response
                appointment_data = json.loads(response.choices[0].message.content)
                span.add_metadata({"extracted_data": appointment_data})
            except json.JSONDecodeError:
                # If not valid JSON, use a fallback
                appointment_data = {"action": "incomplete", "missing": ["all fields"]}
                span.add_metadata({"json_error": response.choices[0].message.content})
        
        # Handle based on the action
        action = appointment_data.get("action", "")
        
        if action == "schedule":
            date = appointment_data.get("date")
            time = appointment_data.get("time")
            reason = appointment_data.get("reason", "Consultation")
            
            if not date or not time:
                # Missing required information
                state["response"] = "I'd be happy to schedule an appointment for you. Could you please specify the date and time you prefer?"
            else:
                # Check available slots
                available_slots = get_available_slots(date)
                
                if not available_slots:
                    # No slots available on that date
                    state["response"] = f"I'm sorry, but we don't have any available appointments on {date}. Would you like to try another date?"
                elif time not in available_slots:
                    # Requested time not available
                    slots_str = ", ".join(available_slots)
                    state["response"] = f"I'm sorry, but {time} is not available on {date}. We have the following slots available: {slots_str}. Would you like to book one of these?"
                else:
                    # Book the appointment
                    appointment = book_appointment(patient_id, date, time, reason)
                    if appointment:
                        # Format the date for better display
                        try:
                            formatted_date = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%A, %B %d, %Y")
                        except:
                            formatted_date = date
                            
                        state["response"] = f"Great! I've booked your appointment for {formatted_date} at {time} with Dr. Smith for {reason}. Please arrive 15 minutes early to complete any necessary paperwork."
                    else:
                        state["response"] = "I'm sorry, but I couldn't book your appointment. Please try again later."
        
        elif action == "cancel":
            # For demo purposes, find the most recent appointment
            patient_appointments = find_appointments(patient_id)
            
            if not patient_appointments:
                state["response"] = "I don't see any appointments scheduled for you. Would you like to book a new appointment?"
            else:
                # Get the first appointment (simplification for demo)
                appointment = patient_appointments[0]
                
                # Cancel the appointment
                cancel_appointment(appointment["id"])
                
                # Format the date for better display
                try:
                    formatted_date = datetime.datetime.strptime(appointment["date"], "%Y-%m-%d").strftime("%A, %B %d, %Y")
                except:
                    formatted_date = appointment["date"]
                    
                state["response"] = f"I've canceled your appointment scheduled for {formatted_date} at {appointment['time']}. Is there anything else I can help you with?"
        
        elif action == "reschedule":
            # For demo purposes, just use the first appointment
            patient_appointments = find_appointments(patient_id)
            
            if not patient_appointments:
                state["response"] = "I don't see any appointments scheduled for you. Would you like to book a new appointment?"
            else:
                # Get the first appointment (simplification for demo)
                old_appointment = patient_appointments[0]
                
                # Get new date and time
                new_date = appointment_data.get("new_date", old_appointment["date"])
                new_time = appointment_data.get("new_time", old_appointment["time"])
                
                # Check if the new slot is available
                available_slots = get_available_slots(new_date)
                
                if new_time not in available_slots:
                    slots_str = ", ".join(available_slots)
                    state["response"] = f"I'm sorry, but {new_time} is not available on {new_date}. We have the following slots available: {slots_str}. Would you like to book one of these?"
                else:
                    # Cancel old appointment
                    cancel_appointment(old_appointment["id"])
                    
                    # Book new appointment
                    book_appointment(
                        patient_id,
                        new_date,
                        new_time,
                        old_appointment["reason"]
                    )
                    
                    # Format the dates for better display
                    try:
                        formatted_old_date = datetime.datetime.strptime(old_appointment["date"], "%Y-%m-%d").strftime("%A, %B %d, %Y")
                        formatted_new_date = datetime.datetime.strptime(new_date, "%Y-%m-%d").strftime("%A, %B %d, %Y")
                    except:
                        formatted_old_date = old_appointment["date"]
                        formatted_new_date = new_date
                    
                    state["response"] = f"I've rescheduled your appointment from {formatted_old_date} at {old_appointment['time']} to {formatted_new_date} at {new_time}. Is there anything else I can help you with?"
        
        else:
            # Incomplete information
            state["response"] = "I'd like to help you with your appointment, but I need a bit more information. Could you please specify whether you want to schedule, reschedule, or cancel an appointment?"
        
        trace.update(status="success")
        
    except Exception as e:
        trace.update(status="error", error={"message": str(e)})
        print(f"Error in appointment agent: {e}")
        state["response"] = "I'm having trouble processing your appointment request. Please try again or contact our office directly."
    
    return state 
import os
from openai import OpenAI
from langfuse.client import Langfuse
import datetime
import json
import re

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

def debug_log(message):
    """Helper function to print debug messages"""
    print(f"DEBUG: {message}")

def parse_date_time(date_str, time_str):
    """
    Parse natural language date and time strings into standardized formats
    
    Args:
        date_str: Natural language date (e.g., "Monday", "tomorrow", "July 10")
        time_str: Natural language time (e.g., "2 p.m.", "14:00", "afternoon")
    
    Returns:
        tuple: (formatted_date, formatted_time) or (None, None) if parsing fails
    """
    try:
        debug_log(f"Parsing date: '{date_str}' and time: '{time_str}'")
        
        # Handle null values
        if not date_str or not time_str:
            debug_log("Date or time string is empty")
            return None, None
            
        # Get current date for reference
        today = datetime.datetime.now()
        
        # Handle relative dates
        date_obj = None
        
        # Convert date_str to lowercase for case-insensitive matching
        date_str_lower = date_str.lower()
        
        if 'today' in date_str_lower:
            date_obj = today
            debug_log(f"Detected 'today', using date: {date_obj.strftime('%Y-%m-%d')}")
        elif 'tomorrow' in date_str_lower:
            date_obj = today + datetime.timedelta(days=1)
            debug_log(f"Detected 'tomorrow', using date: {date_obj.strftime('%Y-%m-%d')}")
        elif 'monday' in date_str_lower:
            # Calculate days until next Monday
            days_ahead = 0 - today.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            date_obj = today + datetime.timedelta(days=days_ahead)
            debug_log(f"Detected 'monday', using date: {date_obj.strftime('%Y-%m-%d')}")
        elif 'tuesday' in date_str_lower:
            days_ahead = 1 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            date_obj = today + datetime.timedelta(days=days_ahead)
            debug_log(f"Detected 'tuesday', using date: {date_obj.strftime('%Y-%m-%d')}")
        elif 'wednesday' in date_str_lower:
            days_ahead = 2 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            date_obj = today + datetime.timedelta(days=days_ahead)
            debug_log(f"Detected 'wednesday', using date: {date_obj.strftime('%Y-%m-%d')}")
        elif 'thursday' in date_str_lower:
            days_ahead = 3 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            date_obj = today + datetime.timedelta(days=days_ahead)
            debug_log(f"Detected 'thursday', using date: {date_obj.strftime('%Y-%m-%d')}")
        elif 'friday' in date_str_lower:
            days_ahead = 4 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            date_obj = today + datetime.timedelta(days=days_ahead)
            debug_log(f"Detected 'friday', using date: {date_obj.strftime('%Y-%m-%d')}")
        elif 'saturday' in date_str_lower:
            days_ahead = 5 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            date_obj = today + datetime.timedelta(days=days_ahead)
            debug_log(f"Detected 'saturday', using date: {date_obj.strftime('%Y-%m-%d')}")
        elif 'sunday' in date_str_lower:
            days_ahead = 6 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            date_obj = today + datetime.timedelta(days=days_ahead)
            debug_log(f"Detected 'sunday', using date: {date_obj.strftime('%Y-%m-%d')}")
        
        # If no day name was matched, try direct parsing
        if date_obj is None:
            try:
                # Try with the standardized format
                date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                debug_log(f"Parsed date in YYYY-MM-DD format: {date_obj.strftime('%Y-%m-%d')}")
            except ValueError:
                try:
                    # Try month/day format
                    date_obj = datetime.datetime.strptime(date_str, "%m/%d")
                    date_obj = date_obj.replace(year=today.year)
                    
                    # If date is in the past, assume next year
                    if date_obj < today:
                        date_obj = date_obj.replace(year=today.year + 1)
                    debug_log(f"Parsed date in MM/DD format: {date_obj.strftime('%Y-%m-%d')}")
                except ValueError:
                    debug_log(f"Failed to parse date string: {date_str}")
                    # If all parsing attempts fail, try direct GPT parsing as a fallback
                    return None, None
        
        # At this point, we have a valid date_obj
        # Format the date as YYYY-MM-DD
        formatted_date = date_obj.strftime("%Y-%m-%d")
        
        # Parse the time
        # First, clean up the time string
        time_str = time_str.strip().lower()
        formatted_time = None
        
        # Handle common time formats with regex
        time_patterns = [
            # 2 p.m. or 2pm
            (r'(\d{1,2})\s*(?::|\.)*\s*(p\.?m\.?)', 
             lambda m: f"{(int(m.group(1)) % 12) + 12}:00"),
            
            # 2 a.m. or 2am
            (r'(\d{1,2})\s*(?::|\.)*\s*(a\.?m\.?)', 
             lambda m: f"{int(m.group(1)) % 12:02d}:00"),
             
            # 2:30 p.m. or 2.30pm
            (r'(\d{1,2})[:\.](\d{2})\s*(p\.?m\.?)', 
             lambda m: f"{(int(m.group(1)) % 12) + 12}:{m.group(2)}"),
             
            # 2:30 a.m. or 2.30am
            (r'(\d{1,2})[:\.](\d{2})\s*(a\.?m\.?)', 
             lambda m: f"{int(m.group(1)) % 12:02d}:{m.group(2)}"),
             
            # 14:00 or 14.00 (24-hour format)
            (r'(\d{1,2})[:\.](\d{2})(?!\s*[ap]\.?m\.?)', 
             lambda m: f"{int(m.group(1)):02d}:{m.group(2)}"),
             
            # Just the hour (e.g., "at 2")
            (r'(?:^|at\s+)(\d{1,2})(?:\s|$)', 
             lambda m: f"{int(m.group(1)) + 12:02d}:00" if 1 <= int(m.group(1)) <= 11 else f"{int(m.group(1)):02d}:00"),
        ]
        
        # Try each pattern
        for pattern, formatter in time_patterns:
            match = re.search(pattern, time_str)
            if match:
                formatted_time = formatter(match)
                debug_log(f"Matched time pattern '{pattern}', formatted as: {formatted_time}")
                break
        
        # If no regex match, try common time descriptions
        if not formatted_time:
            time_mapping = {
                "morning": "09:00",
                "afternoon": "14:00",
                "evening": "16:00",
                "night": "16:30",
                "noon": "12:00",
                "midday": "12:00",
                "lunch": "12:00",
                "breakfast": "08:00",
                "dinner": "18:00"
            }
            
            for time_desc, std_time in time_mapping.items():
                if time_desc in time_str:
                    formatted_time = std_time
                    debug_log(f"Matched time description '{time_desc}', using: {formatted_time}")
                    break
        
        # If we have both date and time, return them
        if formatted_date and formatted_time:
            debug_log(f"Successfully parsed to: date={formatted_date}, time={formatted_time}")
            return formatted_date, formatted_time
        else:
            debug_log(f"Parsing incomplete: date={formatted_date}, time={formatted_time}")
            return formatted_date, formatted_time
    
    except Exception as e:
        debug_log(f"Error parsing date/time: {e}")
        return None, None

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

def extract_date_time_from_transcript(transcript):
    """
    Directly extract date and time from a transcript without using GPT
    
    Args:
        transcript: The patient's transcript
    
    Returns:
        tuple: (date_str, time_str, action)
    """
    transcript = transcript.lower()
    
    # Default values
    date_str = None
    time_str = None
    action = "schedule"  # Default action
    
    # Check for cancellation intent
    if any(word in transcript for word in ["cancel", "delete", "remove"]):
        action = "cancel"
        return date_str, time_str, action
    
    # Check for rescheduling intent
    if any(word in transcript for word in ["reschedule", "change", "move"]):
        action = "reschedule"
    
    # Check for common day patterns
    day_patterns = [
        (r'\b(today)\b', 'today'),
        (r'\b(tomorrow)\b', 'tomorrow'),
        (r'\b(monday|mon)\b', 'monday'),
        (r'\b(tuesday|tues|tue)\b', 'tuesday'),
        (r'\b(wednesday|wed)\b', 'wednesday'),
        (r'\b(thursday|thurs|thu)\b', 'thursday'),
        (r'\b(friday|fri)\b', 'friday'),
        (r'\b(saturday|sat)\b', 'saturday'),
        (r'\b(sunday|sun)\b', 'sunday')
    ]
    
    for pattern, day in day_patterns:
        if re.search(pattern, transcript):
            date_str = day
            break
    
    # Try to find time mentions
    time_patterns = [
        r'\b(\d{1,2})\s*(?::|\.)*\s*(p\.?m\.?)\b',  # 2 p.m.
        r'\b(\d{1,2})\s*(?::|\.)*\s*(a\.?m\.?)\b',  # 2 a.m.
        r'\b(\d{1,2})[:\.](\d{2})\s*(p\.?m\.?)\b',  # 2:30 p.m.
        r'\b(\d{1,2})[:\.](\d{2})\s*(a\.?m\.?)\b',  # 2:30 a.m.
        r'\b(\d{1,2})[:\.](\d{2})\b',               # 14:00
        r'\bat\s+(\d{1,2})\b'                        # at 2
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, transcript)
        if match:
            if 'p.m.' in match.group() or 'pm' in match.group():
                if ':' in match.group() or '.' in match.group():
                    # It's a time with minutes, like 2:30 p.m.
                    hour, minutes = re.findall(r'(\d+)[:\.](\d+)', match.group())[0]
                    time_str = f"{int(hour)} p.m."
                else:
                    # It's just the hour, like 2 p.m.
                    hour = re.findall(r'(\d+)', match.group())[0]
                    time_str = f"{hour} p.m."
            elif 'a.m.' in match.group() or 'am' in match.group():
                if ':' in match.group() or '.' in match.group():
                    # It's a time with minutes, like 9:30 a.m.
                    hour, minutes = re.findall(r'(\d+)[:\.](\d+)', match.group())[0]
                    time_str = f"{int(hour)} a.m."
                else:
                    # It's just the hour, like 9 a.m.
                    hour = re.findall(r'(\d+)', match.group())[0]
                    time_str = f"{hour} a.m."
            elif 'at' in match.group():
                # Just "at X" - assume afternoon for 1-11
                hour = re.findall(r'(\d+)', match.group())[0]
                if 1 <= int(hour) <= 11:
                    time_str = f"{hour} p.m."
                else:
                    time_str = f"{hour}:00"
            else:
                # It's 24-hour format or just has minutes
                time_str = match.group()
            break
    
    # Check for time of day mentions
    time_of_day = [
        (r'\b(morning)\b', 'morning'),
        (r'\b(afternoon)\b', 'afternoon'),
        (r'\b(evening)\b', 'evening'),
        (r'\b(night)\b', 'night')
    ]
    
    if not time_str:
        for pattern, period in time_of_day:
            if re.search(pattern, transcript):
                time_str = period
                break
    
    return date_str, time_str, action

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
        
        # First try direct extraction from transcript
        direct_date_str, direct_time_str, direct_action = extract_date_time_from_transcript(transcript)
        
        debug_log(f"Direct extraction: date={direct_date_str}, time={direct_time_str}, action={direct_action}")
        
        # If we got results from direct extraction, try to parse them
        if direct_date_str and direct_time_str:
            formatted_date, formatted_time = parse_date_time(direct_date_str, direct_time_str)
            if formatted_date and formatted_time:
                # We've successfully extracted and parsed the date/time
                debug_log(f"Using directly extracted date/time: {formatted_date} at {formatted_time}")
                # Set up appointment_data for the rest of the function
                appointment_data = {
                    "action": direct_action,
                    "date": direct_date_str,
                    "time": direct_time_str,
                    "reason": "Consultation"  # Default reason
                }
            else:
                # Failed to parse the extracted date/time, fallback to GPT
                debug_log("Direct extraction failed to parse, falling back to GPT")
                appointment_data = None
        else:
            # Direct extraction didn't find date/time, fallback to GPT
            debug_log("Direct extraction didn't find complete date/time, falling back to GPT")
            appointment_data = None
        
        # If direct extraction failed, use GPT
        if not appointment_data:
            system_prompt = """
            You are an AI appointment assistant for a healthcare clinic. Extract relevant appointment details
            from the patient's request. The patient might provide the date and time in conversational format
            like "Monday at 2pm" or "tomorrow afternoon".
            
            Your task is to extract the INTENT of the patient and the key appointment details.
            
            For scheduling, provide this JSON format:
            {"action": "schedule", "date": "[exact date mentioned or day of week]", "time": "[exact time mentioned]", "reason": "[reason for visit or 'Consultation' if not specified]"}
            
            For cancellation, provide this JSON format:
            {"action": "cancel", "appointment_id": "ID or description of the appointment"}
            
            For rescheduling, provide this JSON format:
            {"action": "reschedule", "appointment_id": "ID or description", "new_date": "[new date]", "new_time": "[new time]"}
            
            If the patient just wants to schedule an appointment but doesn't provide specifics, use:
            {"action": "schedule", "date": null, "time": null, "reason": "Consultation"}
            
            If the patient provides a specific day like "Monday" or "next Tuesday", extract it exactly as mentioned.
            If the patient provides a specific time like "2pm" or "afternoon", extract it exactly as mentioned.
            
            Only output valid JSON without additional text.
            """
            
            # Create a Langfuse span directly without context manager
            span = trace.span(name="gpt4_appointment_extraction")
            
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
                debug_log(f"GPT extracted: {appointment_data}")
                # Create a new span with metadata instead of adding metadata to existing span
                trace.span(name="json_parsing", metadata={"extracted_data": appointment_data})
            except json.JSONDecodeError:
                # If not valid JSON, use a fallback
                debug_log(f"JSON parse error: {response.choices[0].message.content}")
                appointment_data = {"action": "incomplete", "missing": ["all fields"]}
                # Create a new span with error metadata
                trace.span(name="json_error", metadata={"json_error": response.choices[0].message.content})
            
            # End the original span
            span.end()
        
        # Handle based on the action
        action = appointment_data.get("action", "")
        
        if action == "schedule":
            date_str = appointment_data.get("date")
            time_str = appointment_data.get("time")
            reason = appointment_data.get("reason", "Consultation")
            
            debug_log(f"Processing schedule action with date={date_str}, time={time_str}")
            
            # Handle natural language date/time
            if date_str and time_str:
                # Try to parse the natural language date and time
                formatted_date, formatted_time = parse_date_time(date_str, time_str)
                
                if formatted_date and formatted_time:
                    # Successfully parsed date and time
                    date = formatted_date
                    time = formatted_time
                    debug_log(f"Successfully parsed to date={date}, time={time}")
                else:
                    # Parsing failed, just echo back what we got for clarity
                    state["response"] = f"I'd be happy to schedule your appointment, but I need a specific date and time. Could you please provide when you'd like to come in?"
                    return state
            else:
                # Missing required information
                date = None
                time = None
            
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
                new_date_str = appointment_data.get("new_date", old_appointment["date"])
                new_time_str = appointment_data.get("new_time", old_appointment["time"])
                
                # Parse natural language date/time
                parsed_date, parsed_time = parse_date_time(new_date_str, new_time_str)
                new_date = parsed_date if parsed_date else old_appointment["date"]
                new_time = parsed_time if parsed_time else old_appointment["time"]
                
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
        debug_log(f"Error in appointment agent: {e}")
        state["response"] = "I'm having trouble processing your appointment request. Please try again or contact our office directly."
    
    return state 
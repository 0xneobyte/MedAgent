import os
from openai import OpenAI
from langfuse.client import Langfuse
import datetime
import json
import re
from app.models import Patient, Doctor, Appointment

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

# Appointment booking states
STATES = {
    "INITIAL": "initial",
    "COLLECTING_NAME": "collecting_name",
    "COLLECTING_PHONE": "collecting_phone",
    "COLLECTING_BIRTHDATE": "collecting_birthdate",
    "COLLECTING_REASON": "collecting_reason",
    "SUGGESTING_SPECIALTY": "suggesting_specialty",
    "COLLECTING_DATE_TIME": "collecting_date_time",
    "COLLECTING_EMAIL": "collecting_email",
    "CONFIRMING": "confirming",
    "COMPLETED": "completed",
    "CANCELLED": "cancelled"
}

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

def extract_name(transcript):
    """Extract patient name from transcript"""
    # Simple extraction using GPT
    system_prompt = """
    You are a helpful assistant extracting a patient's name from their message.
    Return ONLY the name without any additional text or explanation.
    If you cannot determine a name, respond with "Unknown".
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript}
        ],
        temperature=0.1,
        max_tokens=50
    )
    
    name = response.choices[0].message.content.strip()
    if name.lower() == "unknown":
        return None
        
    return name

def extract_phone(transcript):
    """Extract phone number from transcript"""
    # Try regex first for common formats
    phone_patterns = [
        r'\b(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b',  # 123-456-7890, 123.456.7890, 123 456 7890
        r'\b(\(\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4})\b',  # (123)-456-7890, (123).456.7890, (123) 456 7890
        r'\b(\+\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b',  # +1-123-456-7890
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, transcript)
        if match:
            # Remove non-numeric characters
            phone = re.sub(r'\D', '', match.group(1))
            return phone
    
    # If regex fails, try GPT extraction
    system_prompt = """
    You are a helpful assistant extracting a phone number from a message.
    Return ONLY the phone number without any additional text or explanation.
    Format the number as a continuous string of digits without spaces or special characters.
    If you cannot determine a phone number, respond with "Unknown".
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript}
        ],
        temperature=0.1,
        max_tokens=20
    )
    
    phone = response.choices[0].message.content.strip()
    if phone.lower() == "unknown":
        return None
    
    # Remove any non-numeric characters
    phone = re.sub(r'\D', '', phone)
    if len(phone) < 10:  # Ensure it's a valid phone number
        return None
        
    return phone

def extract_birthdate(transcript):
    """Extract birthdate from transcript"""
    # Try regex for common date formats
    date_patterns = [
        r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b',  # MM/DD/YYYY, DD/MM/YYYY
        r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',  # YYYY/MM/DD
        r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'  # Month DD, YYYY
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, transcript, re.IGNORECASE)
        if match:
            try:
                # Try to parse the date
                date_str = match.group(1)
                # Various parsing attempts based on format
                for fmt in ["%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%m-%d-%Y", "%d-%m-%Y", "%Y-%m-%d"]:
                    try:
                        date_obj = datetime.datetime.strptime(date_str, fmt)
                        # Return in YYYY-MM-DD format
                        return date_obj.strftime("%Y-%m-%d")
                    except ValueError:
                        continue
            except:
                pass
    
    # If regex fails, try GPT extraction
    system_prompt = """
    You are a helpful assistant extracting a birthdate from a message.
    Return ONLY the date in YYYY-MM-DD format without any additional text or explanation.
    If you cannot determine a date, respond with "Unknown".
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript}
        ],
        temperature=0.1,
        max_tokens=20
    )
    
    date = response.choices[0].message.content.strip()
    if date.lower() == "unknown":
        return None
        
    # Validate the date format
    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
        return date
    except ValueError:
        return None

def extract_email(transcript):
    """Extract email from transcript"""
    # Try regex for email format
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, transcript)
    if match:
        return match.group(0)
    
    # If regex fails, try GPT extraction
    system_prompt = """
    You are a helpful assistant extracting an email address from a message.
    Return ONLY the email address without any additional text or explanation.
    If you cannot determine an email address, respond with "Unknown".
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript}
        ],
        temperature=0.1,
        max_tokens=50
    )
    
    email = response.choices[0].message.content.strip()
    if email.lower() == "unknown" or not '@' in email:
        return None
        
    return email

def extract_reason(transcript):
    """Extract reason for visit from transcript"""
    system_prompt = """
    You are a helpful assistant extracting a patient's reason for visiting a doctor from their message.
    Return ONLY the reason without any additional text or explanation.
    Be concise but informative, focusing on symptoms or health concerns.
    If you cannot determine a reason, respond with "Consultation".
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript}
        ],
        temperature=0.1,
        max_tokens=100
    )
    
    reason = response.choices[0].message.content.strip()
    if reason.lower() == "unknown":
        return "Consultation"
        
    return reason

def validate_birthdate(birthdate):
    """Validate birthdate format and ensure it's a past date"""
    try:
        date_obj = datetime.datetime.strptime(birthdate, "%Y-%m-%d")
        today = datetime.datetime.now()
        
        # Check if date is in the past and not more than 120 years ago
        if date_obj > today:
            return False
        
        max_age = today - datetime.timedelta(days=365 * 120)
        if date_obj < max_age:
            return False
            
        return True
    except ValueError:
        return False

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
        
        # Only process if the intent is appointment-related
        if "appointment" not in intent:
            state["response"] = "I'm not sure I understand what you need. Are you trying to schedule an appointment?"
            return state
        
        # Initialize appointment context in the state if it doesn't exist
        if "appointment_context" not in state:
            state["appointment_context"] = {
                "state": STATES["INITIAL"],
                "patient_name": None,
                "patient_phone": None,
                "patient_email": None,
                "patient_birthdate": None,
                "appointment_reason": None,
                "doctor_specialty": None,
                "selected_doctor_id": None,
                "appointment_date": None,
                "appointment_time": None
            }
        
        context = state["appointment_context"]
        
        # Determine action based on current state
        if context["state"] == STATES["INITIAL"]:
            # Transition to name collection
            context["state"] = STATES["COLLECTING_NAME"]
            state["response"] = "I'd be happy to help you schedule an appointment. Could you please tell me your full name?"
        
        elif context["state"] == STATES["COLLECTING_NAME"]:
            # Extract name from transcript
            name = extract_name(transcript)
            
            if name:
                context["patient_name"] = name
                context["state"] = STATES["COLLECTING_PHONE"]
                state["response"] = f"Thank you, {name}. Could you please provide your phone number?"
            else:
                state["response"] = "I need your full name to schedule an appointment. Could you please provide it?"
        
        elif context["state"] == STATES["COLLECTING_PHONE"]:
            # Extract phone from transcript
            phone = extract_phone(transcript)
            
            if phone:
                context["patient_phone"] = phone
                context["state"] = STATES["COLLECTING_BIRTHDATE"]
                state["response"] = "Thank you. Now, could you please share your date of birth in YYYY-MM-DD format?"
            else:
                state["response"] = "I need a valid phone number with at least 10 digits. Could you please provide it?"
        
        elif context["state"] == STATES["COLLECTING_BIRTHDATE"]:
            # Extract birthdate from transcript
            birthdate = extract_birthdate(transcript)
            
            if birthdate and validate_birthdate(birthdate):
                context["patient_birthdate"] = birthdate
                context["state"] = STATES["COLLECTING_REASON"]
                state["response"] = "Thank you. What's the reason for your visit today?"
            else:
                state["response"] = "I need a valid birth date in YYYY-MM-DD format (e.g., 1980-01-15). Could you please provide it?"
        
        elif context["state"] == STATES["COLLECTING_REASON"]:
            # Extract reason from transcript
            reason = extract_reason(transcript)
            
            if reason:
                context["appointment_reason"] = reason
                
                # Determine the specialty based on the reason
                specialty = Doctor.get_specialty_for_reason(reason)
                context["doctor_specialty"] = specialty
                context["state"] = STATES["SUGGESTING_SPECIALTY"]
                
                state["response"] = f"Based on your reason '{reason}', I recommend seeing a {specialty}. Would you like to proceed with this specialist, or would you prefer a different type of doctor?"
            else:
                state["response"] = "I need to know the reason for your visit. Could you please provide more details?"
        
        elif context["state"] == STATES["SUGGESTING_SPECIALTY"]:
            # Check if user agrees with the suggested specialty
            agreement_indicators = ["yes", "sure", "okay", "proceed", "that's fine", "sounds good"]
            disagreement_indicators = ["no", "different", "other", "change", "another", "not that"]
            
            # Default to agreement if no clear indication
            user_agrees = True
            
            for indicator in disagreement_indicators:
                if indicator in transcript.lower():
                    user_agrees = False
                    break
            
            if not user_agrees:
                # Try to extract a different specialty from the transcript
                system_prompt = """
                You are a helpful assistant extracting a medical specialty from a message.
                Return ONLY the medical specialty without any additional text or explanation.
                Examples: Cardiologist, Dermatologist, Neurologist, General Practitioner, etc.
                If you cannot determine a specialty, respond with "General Practitioner".
                """
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": transcript}
                    ],
                    temperature=0.1,
                    max_tokens=20
                )
                
                specialty = response.choices[0].message.content.strip()
                context["doctor_specialty"] = specialty
            
            # Find doctors of this specialty
            doctors = Doctor.find_by_specialty(context["doctor_specialty"])
            
            if not doctors:
                state["response"] = f"I'm sorry, but we don't have any {context['doctor_specialty']} available at the moment. Would you like to see a General Practitioner instead?"
                context["doctor_specialty"] = "General Practitioner"
            else:
                # Select the first doctor for demo purposes
                # In a real app, you would let the user choose
                context["selected_doctor_id"] = doctors[0]["_id"]
                context["state"] = STATES["COLLECTING_DATE_TIME"]
                
                # Get available dates for this doctor
                available_dates = []
                for date in doctors[0]["available_slots"]:
                    if doctors[0]["available_slots"][date]:  # Check if there are slots available
                        formatted_date = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%A, %B %d, %Y")
                        available_dates.append(f"{formatted_date}")
                
                dates_str = ", ".join(available_dates[:3])  # Limit to 3 dates for simplicity
                
                state["response"] = f"I've assigned you to {doctors[0]['name']}, {context['doctor_specialty']}. When would you like to schedule your appointment? We have availability on {dates_str}."
        
        elif context["state"] == STATES["COLLECTING_DATE_TIME"]:
            # Extract date and time from transcript
            date_str, time_str, _ = extract_date_time_from_transcript(transcript)
            
            if date_str and time_str:
                formatted_date, formatted_time = parse_date_time(date_str, time_str)
                
                if formatted_date and formatted_time:
                    # Get doctor object
                    doctor = next((d for d in Doctor.find_by_specialty(context["doctor_specialty"]) 
                                  if str(d["_id"]) == str(context["selected_doctor_id"])), None)
                    
                    if not doctor:
                        state["response"] = "I'm sorry, there was an issue with the selected doctor. Let's start over."
                        context["state"] = STATES["INITIAL"]
                    else:
                        # Check if slot is available
                        available_slots = doctor.get("available_slots", {}).get(formatted_date, [])
                        
                        if formatted_time not in available_slots:
                            slots_str = ", ".join(available_slots[:5])  # Limit to 5 slots for readability
                            
                            if slots_str:
                                state["response"] = f"I'm sorry, but {formatted_time} is not available on that date. Available time slots are: {slots_str}. Would you like to choose one of these times?"
                            else:
                                state["response"] = f"I'm sorry, but there are no available slots on that date. Would you like to try another date?"
                        else:
                            context["appointment_date"] = formatted_date
                            context["appointment_time"] = formatted_time
                            context["state"] = STATES["COLLECTING_EMAIL"]
                            
                            state["response"] = "Great! Now, please provide your email address for the appointment confirmation."
                else:
                    state["response"] = "I couldn't understand the date and time you provided. Could you please specify a date (e.g., Monday, tomorrow) and time (e.g., 2 PM, 14:00)?"
            else:
                state["response"] = "I need both a date and time for your appointment. Could you please provide them?"
        
        elif context["state"] == STATES["COLLECTING_EMAIL"]:
            # Extract email from transcript
            email = extract_email(transcript)
            
            if email:
                context["patient_email"] = email
                context["state"] = STATES["CONFIRMING"]
                
                # Format date for display
                formatted_date = datetime.datetime.strptime(context["appointment_date"], "%Y-%m-%d").strftime("%A, %B %d, %Y")
                
                # Get doctor info
                doctor = next((d for d in Doctor.find_by_specialty(context["doctor_specialty"]) 
                              if str(d["_id"]) == str(context["selected_doctor_id"])), None)
                
                # Create confirmation message
                confirmation = f"Please confirm your appointment details:\n"
                confirmation += f"- Name: {context['patient_name']}\n"
                confirmation += f"- Phone: {context['patient_phone']}\n"
                confirmation += f"- Email: {context['patient_email']}\n"
                confirmation += f"- Date of Birth: {context['patient_birthdate']}\n"
                confirmation += f"- Doctor: {doctor['name']} ({context['doctor_specialty']})\n"
                confirmation += f"- Date: {formatted_date}\n"
                confirmation += f"- Time: {context['appointment_time']}\n"
                confirmation += f"- Reason: {context['appointment_reason']}\n\n"
                confirmation += "Is this information correct? Please say 'yes' to confirm or 'no' to make changes."
                
                state["response"] = confirmation
            else:
                state["response"] = "I need a valid email address for sending the appointment confirmation. Could you please provide it?"
        
        elif context["state"] == STATES["CONFIRMING"]:
            # Check if user confirms
            if "yes" in transcript.lower() or "confirm" in transcript.lower() or "correct" in transcript.lower():
                # Save patient information
                patient_id = Patient.create(
                    name=context["patient_name"],
                    phone=context["patient_phone"],
                    email=context["patient_email"],
                    birthdate=context["patient_birthdate"]
                )
                
                # Book the appointment
                appointment_id = Appointment.create(
                    patient_id=patient_id,
                    doctor_id=context["selected_doctor_id"],
                    date=context["appointment_date"],
                    time=context["appointment_time"],
                    reason=context["appointment_reason"]
                )
                
                # Format date for display
                formatted_date = datetime.datetime.strptime(context["appointment_date"], "%Y-%m-%d").strftime("%A, %B %d, %Y")
                
                # Get doctor info
                doctor = next((d for d in Doctor.find_by_specialty(context["doctor_specialty"]) 
                              if str(d["_id"]) == str(context["selected_doctor_id"])), None)
                
                context["state"] = STATES["COMPLETED"]
                
                # Success response
                state["response"] = f"Great! I've booked your appointment with {doctor['name']} for {formatted_date} at {context['appointment_time']}. A confirmation email has been sent to {context['patient_email']}. Please arrive 15 minutes early to complete any necessary paperwork."
                
                # Store appointment details in state for notification agent
                state["appointment_details"] = {
                    "patient_name": context["patient_name"],
                    "patient_email": context["patient_email"],
                    "doctor_name": doctor["name"],
                    "doctor_specialty": context["doctor_specialty"],
                    "date": context["appointment_date"],
                    "formatted_date": formatted_date,
                    "time": context["appointment_time"],
                    "reason": context["appointment_reason"]
                }
            else:
                # Go back to initial state
                state["response"] = "No problem, let's start over with your appointment booking. What would you like to do?"
                context["state"] = STATES["INITIAL"]
        
        else:
            # Default response for other states
            state["response"] = "I'm here to help with your appointment. What would you like to do?"
            context["state"] = STATES["INITIAL"]
        
        trace.update(status="success")
        
    except Exception as e:
        trace.update(status="error", error={"message": str(e)})
        debug_log(f"Error in appointment agent: {e}")
        state["response"] = "I'm having trouble processing your appointment request. Please try again or contact our office directly."
    
    return state 
import os
from openai import OpenAI
from langfuse.client import Langfuse
import datetime
import json
import re
from app.models import Patient, Doctor, Appointment, patients_collection, doctors_collection, appointments_collection
import random
from dateutil import parser
from bson.objectid import ObjectId

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
    "CANCELLED": "cancelled",
    # New states for cancellation/rescheduling
    "CANCELLING_COLLECTING_ID": "cancelling_collecting_id",
    "CANCELLING_CONFIRMING": "cancelling_confirming",
    "RESCHEDULING_COLLECTING_ID": "rescheduling_collecting_id",
    "RESCHEDULING_DATE_TIME": "rescheduling_date_time",
    "RESCHEDULING_CONFIRMING": "rescheduling_confirming",
    "SCHEDULING_DATE_TIME": "scheduling_date_time",
    "BOOKING_CONFIRMED": "booking_confirmed",
    "CANCELLATION_CONFIRMED": "cancellation_confirmed",
    "RESCHEDULE_CONFIRMED": "reschedule_confirmed"
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
            (r'(\d{1,2})[:\.](\d{2})\s*(p\.?m\.?)\b', 
             lambda m: f"{(int(m.group(1)) % 12) + 12}:{m.group(2)}"),
             
            # 2:30 a.m. or 2.30am
            (r'(\d{1,2})[:\.](\d{2})\s*(a\.?m\.?)\b', 
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

def get_available_slots(date_str):
    """
    Get available appointment slots for a given date
    
    Args:
        date_str: Date string in format YYYY-MM-DD
    
    Returns:
        list: List of available time slots
    """
    debug_log(f"Getting available slots for date: {date_str}")
    
    try:
        # Parse the date 
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        
        # Check if the date is in the past or too far in the future
        today = datetime.datetime.now().date()
        target_date = date_obj.date()
        
        if target_date < today:
            debug_log(f"Date {date_str} is in the past")
            return []
        
        if target_date > today + datetime.timedelta(days=90):
            debug_log(f"Date {date_str} is too far in the future (>90 days)")
            return []
        
        # Check if there are any doctors with available slots on this date
        available_doctors = list(doctors_collection.find(
            {f"available_slots.{date_str}": {"$exists": True}}
        ))
        
        debug_log(f"Found {len(available_doctors)} doctors with availability on {date_str}")
        
        if not available_doctors:
            # If no doctors have explicit availability, use the fallback slots
            # Standard office hours (skipping weekends)
            if date_obj.weekday() >= 5:  # Saturday (5) or Sunday (6)
                debug_log(f"No slots available on weekends unless explicitly set")
                return []
                
            all_slots = [
                "9:00 AM", "9:30 AM", "10:00 AM", "10:30 AM", 
                "11:00 AM", "11:30 AM", "1:00 PM", "1:30 PM",
                "2:00 PM", "2:30 PM", "3:00 PM", "3:30 PM", 
                "4:00 PM", "4:30 PM"
            ]
        else:
            # Collect slots from all available doctors
            all_slots = set()
            for doctor in available_doctors:
                # Check doctor's available slots for this date
                doctor_slots = doctor.get("available_slots", {}).get(date_str, [])
                for slot in doctor_slots:
                    # Convert DB slot format to display format
                    try:
                        # Handle different time formats
                        if ":" in slot:
                            hour, minute = slot.split(":")
                            hour = int(hour)
                            # Convert 24h to 12h format
                            if hour >= 12:
                                period = "PM"
                                if hour > 12:
                                    hour -= 12
                            else:
                                period = "AM"
                                if hour == 0:
                                    hour = 12
                            formatted_slot = f"{hour}:{minute} {period}"
                        else:
                            # Handle format like "10"
                            hour = int(slot)
                            if hour >= 12:
                                period = "PM"
                                if hour > 12:
                                    hour -= 12
                            else:
                                period = "AM"
                                if hour == 0:
                                    hour = 12
                            formatted_slot = f"{hour}:00 {period}"
                            
                        all_slots.add(formatted_slot)
                    except Exception as e:
                        debug_log(f"Error formatting time slot {slot}: {e}")
            
            all_slots = list(all_slots)
        
        # Check existing appointments for this date and remove booked slots
        booked_slots = []
        try:
            # Query MongoDB for appointments on this date
            appointments_for_date = list(appointments_collection.find({"date": date_str, "status": {"$nin": ["cancelled"]}}))
            
            # Extract the times that are already booked
            booked_slots = [appointment["time"] for appointment in appointments_for_date]
            debug_log(f"Found {len(booked_slots)} existing appointments for {date_str}")
        except Exception as e:
            debug_log(f"Error checking existing appointments: {e}")
        
        # Remove booked slots from available slots
        available_slots = [slot for slot in all_slots if slot not in booked_slots]
        
        # Sort the slots by time
        try:
            available_slots.sort(key=lambda x: datetime.datetime.strptime(x, "%I:%M %p"))
        except Exception as e:
            debug_log(f"Error sorting time slots: {e}")
        
        debug_log(f"Available slots for {date_str}: {available_slots}")
        return available_slots
    except Exception as e:
        debug_log(f"Error getting available slots: {e}")
        return []

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
    """Extract name from transcript using GPT"""
    debug_log(f"Extracting name from: '{transcript}'")
    
    # First, check for common patterns where name is directly stated
    # This will help avoid unnecessary API calls for simple cases
    name_patterns = [
        r"(?:my name is|i am|this is|i'm) ([a-zA-Z\s]+)",
        r"([a-zA-Z\s]+) is my name",
        r"name (?:is|:) ([a-zA-Z\s]+)",
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, transcript.lower())
        if match:
            name = match.group(1).strip().title()
            debug_log(f"Regex extracted name: '{name}'")
            return name
    
    # If simple patterns don't match, use GPT
    system_prompt = """
    You are a helpful assistant extracting a patient's name from their message.
    Return ONLY the name without any additional text or explanation.
    If you cannot determine a name with high confidence, respond with "Unknown".
    
    Example inputs and outputs:
    Input: "My name is John Smith"
    Output: John Smith
    
    Input: "I'm Alex Muske"
    Output: Alex Muske
    
    Input: "This is Sarah Johnson"
    Output: Sarah Johnson
    
    Input: "my name is tharushka dinujaya"
    Output: Tharushka Dinujaya
    
    Input: "I'd like to book an appointment"
    Output: Unknown
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ],
            temperature=0.1,
            max_tokens=50
        )
        
        extracted_name = response.choices[0].message.content.strip()
        debug_log(f"GPT extracted name: '{extracted_name}'")
        
        if extracted_name.lower() == "unknown":
            debug_log("GPT couldn't identify a name")
            # If GPT fails, try one more fallback - just use the whole message if it's short
            if len(transcript.split()) <= 4:
                clean_name = transcript.strip().title()
                debug_log(f"Using entire message as name: '{clean_name}'")
                return clean_name
            return None
            
        return extracted_name
        
    except Exception as e:
        debug_log(f"Error in GPT name extraction: {e}")
        # In case of API error, treat the whole input as a name if it's short enough
        if len(transcript.split()) <= 4:
            clean_name = transcript.strip().title()
            debug_log(f"Using entire message as name due to API error: '{clean_name}'")
            return clean_name
        return None

def extract_phone(transcript):
    """Extract phone number from transcript using GPT"""
    debug_log(f"Extracting phone number from: '{transcript}'")
    
    system_prompt = """
    You are a helpful assistant extracting a phone number from a patient's message.
    Return ONLY the phone number, formatted with appropriate dashes or spaces.
    If you cannot identify a phone number with high confidence, respond with "Unknown".
    
    Example inputs and outputs:
    Input: "My phone number is 123-456-7890"
    Output: 123-456-7890
    
    Input: "You can call me at (077) 598-2859"
    Output: 077-598-2859
    
    Input: "I'm at +44 7911 123456"
    Output: +44-7911-123456
    
    Input: "I'd like to book an appointment"
    Output: Unknown
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ],
            temperature=0.1,
            max_tokens=50
        )
        
        extracted = response.choices[0].message.content.strip()
        debug_log(f"GPT extracted phone: '{extracted}'")
        
        if extracted.lower() == "unknown":
            debug_log("GPT couldn't identify a phone number")
            return None
            
        # Ensure the extracted text contains digits
        if any(c.isdigit() for c in extracted):
            return extracted
        
        return None
        
    except Exception as e:
        debug_log(f"Error in GPT phone extraction: {e}")
        return None

def extract_birthdate(transcript):
    """Extract birth date from transcript using GPT"""
    debug_log(f"Extracting birthdate from: '{transcript}'")
    
    system_prompt = """
    You are a helpful assistant extracting a birth date from a patient's message.
    Return ONLY the date in YYYY-MM-DD format without any additional text.
    If you cannot determine a birth date with confidence, respond with "Unknown".
    
    Example inputs and outputs:
    Input: "I was born on 1980-01-15"
    Output: 1980-01-15
    
    Input: "My birth date is January 15, 1980"
    Output: 1980-01-15
    
    Input: "DOB: 01/15/1980"
    Output: 1980-01-15
    
    Input: "I'd like to book an appointment"
    Output: Unknown
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ],
            temperature=0.1,
            max_tokens=50
        )
        
        extracted_date = response.choices[0].message.content.strip()
        debug_log(f"GPT extracted date: '{extracted_date}'")
        
        if extracted_date.lower() == "unknown":
            debug_log("GPT couldn't identify a date")
            return None
            
        # Validate that it's in YYYY-MM-DD format
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
        if re.match(date_pattern, extracted_date):
            return extracted_date
            
        return None
        
    except Exception as e:
        debug_log(f"Error in GPT date extraction: {e}")
        return None

def extract_email(transcript):
    """Extract email from transcript with improved handling"""
    debug_log(f"Extracting email from: '{transcript}'")
    
    # First, try to handle common cases with spaces
    # Remove spaces that might be in email addresses (e.g., "hello @ gmail . com")
    cleaned_transcript = re.sub(r'(\w+)\s+@\s+(\w+)\s+\.\s+(\w+)', r'\1@\2.\3', transcript)
    
    # Also try with just one side having spaces
    cleaned_transcript = re.sub(r'(\w+)\s+@\s*(\w+\.\w+)', r'\1@\2', cleaned_transcript)
    cleaned_transcript = re.sub(r'(\w+)\s*@\s+(\w+\.\w+)', r'\1@\2', cleaned_transcript)
    
    # Try regex for standard email format
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, cleaned_transcript)
    if match:
        email = match.group(0)
        debug_log(f"Extracted email with regex: '{email}'")
        return email
    
    # Try GPT extraction with improved prompt
    system_prompt = """
    You are a helpful assistant extracting an email address from a message.
    Return ONLY the email address without any additional text or explanation.
    
    If the input might contain an email with spaces or unusual formatting, 
    convert it to a proper email format.
    
    Examples:
    - "hello@gmail.com" → hello@gmail.com
    - "hello @ gmail . com" → hello@gmail.com
    - "My email is hello at gmail dot com" → hello@gmail.com
    - "contact me at hello gmail com" → hello@gmail.com
    - "hello adsign gmail.com" → hello@gmail.com
    
    If you cannot determine an email address with high confidence, respond with "Unknown".
    """
    
    try:
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
        debug_log(f"GPT extracted email: '{email}'")
        
        if email.lower() == "unknown":
            debug_log("GPT couldn't identify an email")
            return None
            
        # Validate that it looks like an email
        if '@' in email and '.' in email.split('@')[1]:
            return email
            
        return None
        
    except Exception as e:
        debug_log(f"Error in GPT email extraction: {e}")
        return None

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
    """Validate that the birthdate is a valid date and reasonable (not too recent or old)"""
    try:
        if not birthdate:
            return False
            
        # Validate format
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', birthdate):
            return False
            
        # Parse the date
        date_obj = datetime.datetime.strptime(birthdate, "%Y-%m-%d")
        
        # Ensure it's not in the future
        if date_obj > datetime.datetime.now():
            return False
            
        # Ensure it's not unreasonably old (200 years ago)
        if date_obj < datetime.datetime.now() - datetime.timedelta(days=365*200):
            return False
            
        # Get the year to check age range
        current_year = datetime.datetime.now().year
        birth_year = date_obj.year
        age = current_year - birth_year
        
        # Typical patient age range check (0-120 years)
        if age < 0 or age > 120:
            return False
            
        return True
    except ValueError:
        return False

def get_step_prompt(step, context=None):
    """
    Get the appropriate prompt for a given step
    
    Args:
        step: The current step in the workflow
        context: Optional context for formatting the prompt
        
    Returns:
        str: The prompt text for the current step
    """
    prompts = {
        "collecting_name": "To book your appointment, I'll need to collect some information. First, please provide your full name.",
        "collecting_phone": "Thank you. Now, please provide your phone number.",
        "collecting_birthdate": "Great. Now, please provide your date of birth (MM/DD/YYYY).",
        "collecting_reason": "Thanks. What's the reason for your appointment?",
        "suggesting_specialty": "Based on your needs, I recommend seeing {specialty} - {description}. Does this work for you?",
        "collecting_date_time": "When would you like to schedule your appointment? We have available slots on {dates}",
        "rescheduling_date_time": "When would you like to reschedule your appointment to? We have the following available slots: {dates}",
        "collecting_email": "Great! Now, please provide your email address for the appointment confirmation.",
        "confirming": "Great! Here's a summary of your appointment:\n\n{summary}\n\nIs this information correct? Please say 'yes' to confirm or 'no' to make changes.",
        # Clear prompts for cancellation and rescheduling
        "cancelling_collecting_id": "I can help you cancel your appointment. Please provide your appointment ID. It should be in the format MA-##### (e.g., MA-00001) and was included in your confirmation email.",
        "cancelling_confirming": "I found your appointment with {doctor_name} on {formatted_date} at {time}. Are you sure you want to cancel this appointment? Please confirm by saying 'yes' or 'no'.",
        "rescheduling_collecting_id": "I can help you reschedule your appointment. Please provide your appointment ID. It should be in the format MA-##### (e.g., MA-00001) and was included in your confirmation email."
    }
    
    # Get the prompt template
    template = prompts.get(step, "I'm not sure what information to collect next.")
    
    # Format with context if provided
    if context:
        try:
            return template.format(**context)
        except Exception as e:
            debug_log(f"Error formatting prompt template: {e}")
            return template
    
    return template

def extract_date_time_gpt(transcript):
    """Extract date and time from transcript using GPT"""
    debug_log(f"Extracting date and time from: '{transcript}'")
    
    # Get current date to determine the default year
    current_year = datetime.datetime.now().year
    
    system_prompt = f"""
    You are a helpful assistant extracting a date and time from a patient's message.
    The current year is {current_year}. When a year is not specified, use 2025 as the default year.
    
    Return your answer in JSON format with the following structure:
    {{
        "date": "YYYY-MM-DD",
        "time": "HH:MM",
        "action": "schedule"
    }}
    
    For the date, convert all formats to YYYY-MM-DD, ensuring the year is 2025 if not specified.
    For the time, convert all formats to 24-hour time (HH:MM).
    For action, use "schedule" by default, "reschedule" if changing an appointment, or "cancel" for cancellation.
    
    If you cannot determine a date or time with confidence, set the value to null.
    
    Example inputs and outputs:
    Input: "I want an appointment on March 15 at 2pm"
    Output: {{"date": "2025-03-15", "time": "14:00", "action": "schedule"}}
    
    Input: "Book me for tomorrow afternoon"
    Output: {{"date": "2025-03-16", "time": "14:00", "action": "schedule"}}
    
    Input: "I'd like to come in on the 15th at 2"
    Output: {{"date": "2025-03-15", "time": "14:00", "action": "schedule"}}
    
    Input: "Cancel my appointment on Friday"
    Output: {{"date": "2025-03-21", "time": null, "action": "cancel"}}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ],
            temperature=0.1,
            max_tokens=150,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        debug_log(f"GPT extracted date/time: {result}")
        
        # Ensure the year is 2025 for detected dates
        if result.get("date") and "-" in result.get("date", ""):
            parts = result["date"].split("-")
            if len(parts) == 3 and parts[0] == "2024":
                # Replace 2024 with 2025
                result["date"] = f"2025-{parts[1]}-{parts[2]}"
                debug_log(f"Corrected year to 2025: {result['date']}")
        
        return result.get("date"), result.get("time"), result.get("action", "schedule")
        
    except Exception as e:
        debug_log(f"Error in GPT date/time extraction: {e}")
        return None, None, "schedule"

def extract_appointment_id(transcript):
    """Extract appointment ID from transcript"""
    debug_log(f"Extracting appointment ID from: '{transcript}'")
    
    # Try regex for appointment ID format (MA-#####)
    id_pattern = r'(MA-\d{5})'
    match = re.search(id_pattern, transcript)
    if match:
        appointment_id = match.group(1)
        debug_log(f"Extracted appointment ID with regex: '{appointment_id}'")
        return appointment_id
    
    # Try GPT extraction
    system_prompt = """
    You are a helpful assistant extracting an appointment ID from a message.
    Return ONLY the appointment ID without any additional text or explanation.
    
    The appointment ID format is MA-##### (e.g., MA-00001).
    
    If you cannot determine an appointment ID with high confidence, respond with "Unknown".
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ],
            temperature=0.1,
            max_tokens=50
        )
        
        extracted_id = response.choices[0].message.content.strip()
        debug_log(f"GPT extracted appointment ID: '{extracted_id}'")
        
        if extracted_id.lower() == "unknown":
            debug_log("GPT couldn't identify an appointment ID")
            return None
            
        # Validate that it looks like an appointment ID
        if re.match(r'^MA-\d{5}$', extracted_id):
            return extracted_id
            
        return None
        
    except Exception as e:
        debug_log(f"Error in GPT appointment ID extraction: {e}")
        return None

def extract_date_time_action(transcript):
    """
    Extract date, time, and action from a transcript
    
    Args:
        transcript: User input text
    
    Returns:
        dict: Result containing success status, extracted date/time values, and message if applicable
    """
    debug_log(f"Extracting date/time/action from: '{transcript}'")
    try:
        # First try with GPT extraction
        date_str, time_str, action = extract_date_time_gpt(transcript)
        debug_log(f"GPT extraction: date={date_str}, time={time_str}, action={action}")
        
        # If we only have a date but no time, return partial success and ask for time
        if date_str and not time_str:
            try:
                # Parse the date string to ensure it's valid
                parsed_date = parser.parse(date_str)
                date_str = parsed_date.strftime("%Y-%m-%d")
                debug_log(f"Parsed date to: {date_str}")
                
                return {
                    "success": False,
                    "date": date_str,
                    "need_time": True,
                    "message": f"I have the date ({parsed_date.strftime('%A, %B %d, %Y')}), but what time would you prefer for your appointment?"
                }
            except Exception as e:
                debug_log(f"Error parsing date '{date_str}': {e}")
        
        if not date_str and not time_str:
            return {
                "success": False,
                "message": "I couldn't understand the date and time. Please specify a clear date and time, like 'March 20 at 2pm'."
            }
        
        # If we have a date, ensure it's in YYYY-MM-DD format
        if date_str:
            try:
                # Parse the date string to ensure it's valid
                parsed_date = parser.parse(date_str)
                date_str = parsed_date.strftime("%Y-%m-%d")
                debug_log(f"Parsed date to: {date_str}")
            except Exception as e:
                debug_log(f"Error parsing date '{date_str}': {e}")
                return {
                    "success": False,
                    "message": f"I had trouble understanding the date '{date_str}'. Please provide a date in a clear format like 'March 20, 2025'."
                }
        else:
            return {
                "success": False,
                "message": "I couldn't identify a date in your message. Please specify when you'd like to schedule your appointment."
            }
        
        # If we have time, convert to standard format
        if time_str:
            # Normalize time to standard display format (e.g., "2:00 PM")
            try:
                parsed_time = parser.parse(time_str)
                time_str = parsed_time.strftime("%-I:%M %p")
                debug_log(f"Parsed time to: {time_str}")
            except Exception as e:
                debug_log(f"Error parsing time '{time_str}': {e}")
                return {
                    "success": False,
                    "message": f"I had trouble understanding the time '{time_str}'. Please provide a time in a clear format like '2:30 PM'."
                }
        else:
            return {
                "success": False,
                "message": "I couldn't identify a time in your message. Please specify what time you'd like for your appointment."
            }
        
        return {
            "success": True,
            "date": date_str,
            "time": time_str,
            "action": action
        }
        
    except Exception as e:
        debug_log(f"Error in extract_date_time_action: {e}")
        import traceback
        debug_log(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "message": "I had trouble understanding your request. Please specify a date and time for your appointment clearly."
        }

def get_doctor_available_slots(doctor_id, date_str):
    """
    Get available appointment slots for a specific doctor on a given date
    
    Args:
        doctor_id: The doctor's ID
        date_str: Date string in format YYYY-MM-DD
    
    Returns:
        list: List of available time slots for this doctor
    """
    debug_log(f"Getting available slots for doctor {doctor_id} on date: {date_str}")
    
    try:
        # Get the doctor from the database - ensure we convert string ID to ObjectId if needed
        if isinstance(doctor_id, str) and not doctor_id.startswith('ObjectId'):
            try:
                doctor_id = ObjectId(doctor_id)
                debug_log(f"Converted string ID to ObjectID: {doctor_id}")
            except Exception as e:
                debug_log(f"Error converting doctor_id to ObjectID: {e}")
        
        debug_log(f"Looking up doctor with ID: {doctor_id}")
        doctor = doctors_collection.find_one({"_id": doctor_id})
        
        if not doctor:
            debug_log(f"Doctor not found with ID: {doctor_id}")
            return []
            
        debug_log(f"Found doctor: {doctor.get('name', 'Unknown')} with data: {doctor}")
        
        # Check if doctor has slots for this date
        available_slots = []
        
        # BUGFIX: First check if the date exists in the doctor's available_slots
        if 'available_slots' not in doctor or date_str not in doctor['available_slots']:
            debug_log(f"Date {date_str} not found in doctor's available slots")
            return []  # Return empty list if the date doesn't exist
        
        # Get the raw slots from the doctor's schedule
        raw_slots = doctor['available_slots'].get(date_str, [])
        debug_log(f"Raw slots from doctor's schedule for {date_str}: {raw_slots}")
        
        # Format slots for display
        for slot in raw_slots:
            try:
                # Parse the time format from database
                if ":" in slot:
                    hour, minute = slot.split(":")
                    hour = int(hour)
                    minute = minute.zfill(2)  # Ensure two digits
                else:
                    hour = int(slot)
                    minute = "00"
                
                # Convert to 12-hour format
                if hour == 0:
                    display_hour = 12
                    period = "AM"
                elif hour < 12:
                    display_hour = hour
                    period = "AM"
                elif hour == 12:
                    display_hour = 12
                    period = "PM"
                else:
                    display_hour = hour - 12
                    period = "PM"
                
                # Format time as 12-hour format with AM/PM
                formatted_slot = f"{display_hour}:{minute} {period}"
                available_slots.append(formatted_slot)
                debug_log(f"Converted {slot} to {formatted_slot}")
            except Exception as e:
                debug_log(f"Error formatting slot {slot}: {e}")
        
        # Check existing appointments for this doctor on this date
        doctor_id_str = str(doctor_id)
        debug_log(f"Searching for appointments with doctor_id: {doctor_id_str}")
        
        appointments = appointments_collection.find({
            "doctor_id": doctor_id_str,  # Convert ObjectId to string for comparison
            "date": date_str,
            "status": {"$nin": ["cancelled"]}
        })
        
        # Extract booked slots
        booked_slots = [appointment["time"] for appointment in appointments]
        debug_log(f"Booked slots: {booked_slots}")
        
        # Remove booked slots
        available_slots = [slot for slot in available_slots if slot not in booked_slots]
        
        # Sort by time
        available_slots.sort(key=lambda x: datetime.datetime.strptime(x, "%I:%M %p"))
        
        debug_log(f"Final available slots: {available_slots}")
        return available_slots
        
    except Exception as e:
        debug_log(f"Error getting doctor's available slots: {str(e)}")
        import traceback
        debug_log(f"Traceback: {traceback.format_exc()}")
        return []

def appointment_agent(state):
    """
    The main Appointment Agent function for LangGraph
    
    Args:
        state: The current state object from LangGraph
    
    Returns:
        dict: Updated state with appointment handling
    """
    # Extract transcript and intent
    transcript = state.get("transcript", "")
    intent = state.get("intent", "")
    
    debug_log(f"Appointment agent received state: {state}")
    
    # Initialize or get appointment context
    context = state.get("appointment_context", {})
    
    if not context:
        debug_log("Creating new appointment_context")
        context = {
            "state": STATES["INITIAL"],
            "patient_name": None,
            "patient_phone": None,
            "patient_email": None,
            "patient_birthdate": None,
            "appointment_reason": None,
            "doctor_specialty": None,
            "selected_doctor_id": None,
            "appointment_date": None,
            "appointment_time": None,
            "attempts": {
                "name": 0,
                "phone": 0, 
                "birthdate": 0,
                "reason": 0
            }
        }
    else:
        debug_log(f"Using existing appointment_context: {context}")
    
    # Create a trace in Langfuse
    trace = langfuse.trace(
        name="appointment_agent",
        metadata={
            "transcript": state.get("transcript", ""),
            "intent": state.get("intent", "unknown")
        }
    )
    
    try:
        # Analyze the current state and transcript together to determine the correct action
        current_state = context.get("state", STATES["INITIAL"])
        debug_log(f"Current appointment state: {current_state}")
        
        # Check if we're in the middle of a cancellation flow, prioritize that context
        in_cancellation_flow = (
            current_state == STATES["CANCELLING_COLLECTING_ID"] or
            current_state == STATES["CANCELLING_CONFIRMING"] or
            current_state == STATES["CANCELLATION_CONFIRMED"]
        )
        
        # Check if we're in the middle of a rescheduling flow
        in_rescheduling_flow = (
            current_state == STATES["RESCHEDULING_COLLECTING_ID"] or
            current_state == STATES["RESCHEDULING_DATE_TIME"] or
            current_state == STATES["RESCHEDULING_CONFIRMING"] or
            current_state == STATES["RESCHEDULE_CONFIRMED"]
        )
        
        # Check if we're in the middle of a booking flow
        in_booking_flow = (
            current_state != STATES["INITIAL"] and 
            not in_cancellation_flow and 
            not in_rescheduling_flow
        )
        
        # Detect explicit cancellation intent in the transcript
        has_cancel_keyword = "cancel" in transcript.lower()
        # Detect explicit reschedule intent in the transcript
        has_reschedule_keyword = "reschedule" in transcript.lower() or "change appointment" in transcript.lower()
        
        # Override detection: If user explicitly mentions cancel/reschedule, we should handle that
        # even if we're in another flow
        if has_cancel_keyword and not in_cancellation_flow:
            debug_log("Explicit cancellation intent detected, switching to cancellation flow")
            context["state"] = STATES["CANCELLING_COLLECTING_ID"]
            state["response"] = get_step_prompt("cancelling_collecting_id")
            state["intent"] = "cancel_appointment"
            state["appointment_context"] = context
            return state
            
        if has_reschedule_keyword and not in_rescheduling_flow:
            debug_log("Explicit rescheduling intent detected, switching to rescheduling flow")
            context["state"] = STATES["RESCHEDULING_COLLECTING_ID"]
            state["response"] = get_step_prompt("rescheduling_collecting_id")
            state["intent"] = "reschedule_appointment"
            state["appointment_context"] = context
            return state
        
        # Now handle the specific states with improved logic
        if current_state == STATES["INITIAL"]:
            # At the initial state, determine the right flow based on intent
            if intent == "cancel_appointment" or has_cancel_keyword:
                debug_log("Detected cancellation intent from initial state")
                context["state"] = STATES["CANCELLING_COLLECTING_ID"]
                state["response"] = get_step_prompt("cancelling_collecting_id")
                state["intent"] = "cancel_appointment"
            elif intent == "reschedule_appointment" or has_reschedule_keyword:
                debug_log("Detected rescheduling intent from initial state")
                context["state"] = STATES["RESCHEDULING_COLLECTING_ID"]
                state["response"] = get_step_prompt("rescheduling_collecting_id")
                state["intent"] = "reschedule_appointment"
            elif intent == "schedule_appointment" or intent == "book_appointment":
                debug_log("Starting new appointment booking flow")
                context["state"] = STATES["COLLECTING_NAME"]
                state["response"] = get_step_prompt("collecting_name")
            else:
                debug_log(f"Unknown intent in initial state: {intent}")
                state["response"] = "I can help you schedule, reschedule, or cancel an appointment. What would you like to do?"
        
        elif current_state == STATES["CANCELLING_COLLECTING_ID"]:
            # Extract appointment ID
            appointment_id = extract_appointment_id(transcript)
            debug_log(f"Extracted appointment ID: {appointment_id}")
            
            if appointment_id:
                # Look up the appointment
                appointment = Appointment.find_by_appointment_id(appointment_id)
                debug_log(f"Found appointment: {appointment}")
                
                if appointment:
                    try:
                        # Get more details about the appointment
                        patient = patients_collection.find_one({"_id": appointment["patient_id"]})
                        doctor_id = appointment["doctor_id"]
                        debug_log(f"Original doctor_id from appointment: {doctor_id} (type: {type(doctor_id)})")
                        
                        # Look up doctor information
                        doctor = None
                        try:
                            # First try with ObjectId if it's a string
                            if isinstance(doctor_id, str) and not doctor_id.startswith('ObjectId'):
                                doctor_id_obj = ObjectId(doctor_id)
                                doctor = doctors_collection.find_one({"_id": doctor_id_obj})
                                
                            # If that didn't work, try other methods
                            if not doctor:
                                doctor = doctors_collection.find_one({"_id": doctor_id})
                                
                            # If still nothing, try specialty lookup
                            if not doctor and "specialty" in appointment:
                                doctors = Doctor.find_by_specialty(appointment["specialty"])
                                if doctors and len(doctors) > 0:
                                    doctor = doctors[0]
                        except Exception as e:
                            debug_log(f"Error looking up doctor: {e}")
                        
                        # Default doctor name if lookup fails
                        doctor_name = "Dr. Smith"
                        if doctor and "name" in doctor:
                            doctor_name = doctor["name"]
                        
                        # Format date for display
                        formatted_date = datetime.datetime.strptime(appointment["date"], "%Y-%m-%d").strftime("%A, %B %d, %Y")
                        
                        # Save to context
                        context["cancellation_appointment_id"] = appointment_id
                        context["cancellation_appointment"] = {
                            "doctor_name": doctor_name,
                            "formatted_date": formatted_date,
                            "time": appointment["time"],
                            "patient_name": patient["name"] if patient else "Unknown Patient"
                        }
                        
                        # IMPORTANT: Ensure we maintain the cancellation intent
                        state["intent"] = "cancel_appointment"
                        
                        # Move to confirmation step
                        context["state"] = STATES["CANCELLING_CONFIRMING"]
                        confirmation_context = context["cancellation_appointment"]
                        state["response"] = get_step_prompt("cancelling_confirming", confirmation_context)
                    except Exception as e:
                        debug_log(f"Error getting appointment details: {e}")
                        # Even on error, maintain the cancellation context
                        state["intent"] = "cancel_appointment"
                        state["response"] = "I'm sorry, but I encountered an error retrieving your appointment details. Please try again."
                else:
                    # Even if appointment not found, maintain the cancellation context
                    state["intent"] = "cancel_appointment"
                    state["response"] = f"I'm sorry, but I couldn't find an appointment with ID {appointment_id}. Please check the ID and try again."
            else:
                # Even if no ID extracted, maintain the cancellation context
                state["intent"] = "cancel_appointment"
                state["response"] = "I couldn't identify an appointment ID in your message. Please provide your appointment ID in the format MA-##### (e.g., MA-00001)."
        
        elif current_state == STATES["CANCELLING_CONFIRMING"]:
            # Check if user confirms
            confirmation = "yes" in transcript.lower() or "confirm" in transcript.lower()
            
            if confirmation:
                # Cancel the appointment
                try:
                    appointment_id = context["cancellation_appointment_id"]
                    success = Appointment.cancel(appointment_id)
                    
                    if success:
                        # Format a nice response with appointment details
                        appointment_details = context["cancellation_appointment"]
                        doctor_name = appointment_details.get('doctor_name', 'Unknown Doctor')
                        formatted_date = appointment_details.get('formatted_date', 'Unknown Date')
                        time = appointment_details.get('time', 'Unknown Time')
                        patient_name = appointment_details.get('patient_name', 'Unknown Patient')
                        
                        # Try to get patient email if available
                        patient_email = None
                        try:
                            # Get the appointment to find the patient
                            appointment = Appointment.find_by_appointment_id(appointment_id)
                            if appointment and appointment.get("patient_id"):
                                # Look up the patient to get their email
                                patient = patients_collection.find_one({"_id": appointment["patient_id"]})
                                if patient and patient.get("email"):
                                    patient_email = patient["email"]
                                    debug_log(f"Found patient email for cancellation: {patient_email}")
                        except Exception as e:
                            debug_log(f"Error retrieving patient email: {e}")
                        
                        # Update the intent to indicate cancellation
                        state["intent"] = "cancel_appointment"
                        
                        # Store cancellation details in both state and context
                        cancellation_details = {
                            "appointment_id": appointment_id,
                            "patient_name": patient_name,
                            "patient_email": patient_email,  # This will be the actual email or None
                            "doctor_name": doctor_name,
                            "date": appointment_details.get('date'),
                            "formatted_date": formatted_date,
                            "time": time
                        }
                        
                        # Add to state (this might get lost in the workflow)
                        state["cancellation_details"] = cancellation_details
                        
                        # Add to appointment_context (this should persist)
                        if "appointment_context" not in state:
                            state["appointment_context"] = {}
                        state["appointment_context"]["cancellation_details"] = cancellation_details
                        
                        # Log the cancellation details (for debugging)
                        debug_log(f"Setting cancellation details in state: {state['cancellation_details']}")
                        debug_log(f"Setting cancellation details in context: {state['appointment_context']['cancellation_details']}")
                        debug_log(f"Current state intent: {state['intent']}")
                        
                        # Construct response with available details
                        state["response"] = f"I've cancelled your appointment with {doctor_name} on {formatted_date} at {time}. Thank you for letting us know."
                        
                        # Reset the state to CANCELLATION_CONFIRMED instead of INITIAL
                        context["state"] = STATES["CANCELLATION_CONFIRMED"]
                    else:
                        state["response"] = "I'm sorry, but I couldn't cancel your appointment. Please call our office for assistance."
                except Exception as e:
                    debug_log(f"Error cancelling appointment: {e}")
                    state["response"] = "I'm sorry, but I encountered an error while trying to cancel your appointment. Please try again or call our office."
            else:
                state["response"] = "I understand you don't want to cancel your appointment. Is there anything else I can help you with?"
                context["state"] = STATES["INITIAL"]
                
        elif current_state == STATES["RESCHEDULING_COLLECTING_ID"]:
            # Extract appointment ID
            appointment_id = extract_appointment_id(transcript)
            if appointment_id:
                # Look up the appointment
                appointment = Appointment.find_by_appointment_id(appointment_id)
                debug_log(f"Found appointment: {appointment}")
                
                if appointment:
                    # Get more details about the appointment
                    try:
                        patient = patients_collection.find_one({"_id": appointment["patient_id"]})
                        doctor_id = appointment["doctor_id"]
                        debug_log(f"Original doctor_id from appointment: {doctor_id} (type: {type(doctor_id)})")
                        
                        # Ensure doctor_id is properly formatted for lookup
                        if isinstance(doctor_id, str) and not doctor_id.startswith('ObjectId'):
                            try:
                                debug_log(f"Converting string doctor_id to ObjectId: {doctor_id}")
                                doctor_id_obj = ObjectId(doctor_id)
                                doctor = doctors_collection.find_one({"_id": doctor_id_obj})
                                debug_log(f"Doctor lookup result with ObjectId: {doctor}")
                                if not doctor:
                                    # If conversion fails, try as string
                                    doctor = doctors_collection.find_one({"_id": doctor_id})
                                    debug_log(f"Doctor lookup result with string: {doctor}")
                            except Exception as e:
                                debug_log(f"Error converting doctor_id: {e}")
                                # If conversion fails, try as string
                                doctor = doctors_collection.find_one({"_id": doctor_id})
                                debug_log(f"Doctor lookup result with string: {doctor}")
                        else:
                            doctor = doctors_collection.find_one({"_id": doctor_id})
                            debug_log(f"Doctor lookup result: {doctor}")
                        
                        # Format date for display
                        formatted_date = datetime.datetime.strptime(appointment["date"], "%Y-%m-%d").strftime("%A, %B %d, %Y")
                        
                        # Save to context - store doctor_id as string to avoid JSON serialization issues
                        context["reschedule_appointment_id"] = appointment_id
                        context["reschedule_appointment"] = {
                            "doctor_name": doctor["name"] if doctor else "Unknown Doctor",
                            "doctor_id": str(doctor_id_obj) if 'doctor_id_obj' in locals() else str(doctor_id),
                            "formatted_date": formatted_date,
                            "date": appointment["date"],
                            "time": appointment["time"],
                            "patient_name": patient["name"] if patient else "Unknown Patient"
                        }
                        
                        # Check if doctor has available slots
                        today = datetime.datetime.now().date()
                        available_dates = []
                        
                        # Check next 10 days for available slots
                        for i in range(1, 11):
                            check_date = today + datetime.timedelta(days=i)
                            check_date_str = check_date.strftime("%Y-%m-%d")
                            
                            # Get slots specifically for this doctor
                            slots = get_doctor_available_slots(doctor_id, check_date_str)
                            
                            if slots:
                                formatted_check_date = check_date.strftime("%A, %B %d")
                                available_dates.append({
                                    "date": check_date_str,
                                    "formatted_date": formatted_check_date,
                                    "slots": slots
                                })
                                if len(available_dates) >= 3:  # Show next 3 available dates
                                    break
                        
                        # Move to date/time collection step
                        context["state"] = STATES["RESCHEDULING_DATE_TIME"]
                        context["available_dates"] = available_dates
                        
                        # Prepare response with appointment details and available slots
                        doctor_name = doctor["name"] if doctor else "Unknown Doctor"
                        response = f"I've found your current appointment on {formatted_date} at {appointment['time']} with {doctor_name}. "
                        
                        if available_dates:
                            response += f"Here are available time slots with {doctor_name}:"
                            for date_info in available_dates:
                                # Format the date with calendar emoji
                                response += f"\n\n📅 {date_info['formatted_date']}:"
                                slots_to_show = date_info['slots']
                                
                                # Group time slots by morning/afternoon for better readability
                                morning_slots = [slot for slot in slots_to_show if "AM" in slot]
                                afternoon_slots = [slot for slot in slots_to_show if "PM" in slot]
                                
                                if morning_slots:
                                    response += f"\nMorning: • {' • '.join(morning_slots)}"
                                
                                if afternoon_slots:
                                    response += f"\nAfternoon: • {' • '.join(afternoon_slots)}"
                            
                            response += "\n\nPlease select a date and time for your new appointment."
                        else:
                            response += f"I'm sorry, but {doctor_name} doesn't have any available slots in the next 10 days. Please call our office to check for other options."
                        
                        state["response"] = response
                    except Exception as e:
                        debug_log(f"Error getting appointment details: {e}")
                        state["response"] = "I'm sorry, but I encountered an error retrieving your appointment details. Please try again."
                else:
                    state["response"] = f"I'm sorry, but I couldn't find an appointment with ID {appointment_id}. Please check the ID and try again."
            else:
                state["response"] = "I couldn't identify an appointment ID in your message. Please provide your appointment ID in the format MA-##### (e.g., MA-00001)."
                
        elif current_state == STATES["RESCHEDULING_DATE_TIME"]:
            # Extract date and time from transcript
            debug_log(f"Processing rescheduling date/time from transcript: '{transcript}'")
            
            # Get the doctor information
            doctor_id = context["reschedule_appointment"]["doctor_id"]
            doctor_name = context["reschedule_appointment"]["doctor_name"]
            
            # Extract date and time
            date_time_result = extract_date_time_action(transcript)
            debug_log(f"Date time extraction result: {date_time_result}")
            
            # Special case: If we got a date but need time
            if not date_time_result.get("success") and date_time_result.get("need_time") and date_time_result.get("date"):
                # Store the date for later use
                date_str = date_time_result["date"]
                
                # BUGFIX: Check if this date exists in the doctor's schedule first
                doctor_obj = doctors_collection.find_one({"_id": ObjectId(doctor_id)})
                if not doctor_obj or 'available_slots' not in doctor_obj or date_str not in doctor_obj['available_slots']:
                    state["response"] = f"I'm sorry, but {doctor_name} is not available on {parser.parse(date_str).strftime('%A, %B %d, %Y')}. Please select one of the dates I mentioned earlier."
                    return state
                
                # Get the available slots for this date to show to the user
                doctor_slots = get_doctor_available_slots(doctor_id, date_str)
                
                if doctor_slots:
                    formatted_date = parser.parse(date_str).strftime('%A, %B %d, %Y')
                    
                    # Group times into morning and afternoon
                    morning_slots = [slot for slot in doctor_slots if "AM" in slot]
                    afternoon_slots = [slot for slot in doctor_slots if "PM" in slot]
                    
                    response = f"For {formatted_date}, we have the following appointment times available with {doctor_name}:\n\n"
                    
                    if morning_slots:
                        response += f"Morning: • {' • '.join(morning_slots)}\n"
                    
                    if afternoon_slots:
                        response += f"Afternoon: • {' • '.join(afternoon_slots)}\n"
                    
                    response += "\nPlease select a time for your appointment."
                    state["response"] = response
                else:
                    state["response"] = f"I'm sorry, but there are no available slots on {parser.parse(date_str).strftime('%A, %B %d, %Y')} with {doctor_name}. Please select a different date."
                
                return state
            
            if date_time_result.get("success"):
                date_str = date_time_result["date"]
                time_str = date_time_result["time"]
                
                # Verify the slot is available for this specific doctor
                doctor_slots = get_doctor_available_slots(doctor_id, date_str)
                
                if time_str in doctor_slots:
                    # We found a valid slot - save it for confirmation
                    context["new_appointment_date"] = date_str
                    context["new_appointment_time"] = time_str
                    
                    # Format dates for display
                    old_date = context["reschedule_appointment"]["date"]
                    old_time = context["reschedule_appointment"]["time"]
                    old_formatted_date = context["reschedule_appointment"]["formatted_date"]
                    new_formatted_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").strftime("%A, %B %d, %Y")
                    
                    # Move to confirmation
                    context["state"] = STATES["RESCHEDULING_CONFIRMING"]
                    
                    # Prepare confirmation
                    confirmation_context = {
                        "doctor_name": doctor_name,
                        "old_date": old_formatted_date,
                        "old_time": old_time,
                        "new_date": new_formatted_date,
                        "new_time": time_str
                    }
                    
                    state["response"] = f"I'm rescheduling your appointment with {doctor_name} from {old_formatted_date} at {old_time} to {new_formatted_date} at {time_str}. Is this correct? Please confirm by saying 'yes' or 'no'."
                else:
                    # Time not available for this doctor
                    if doctor_slots:
                        state["response"] = f"I'm sorry, but {time_str} is not available with {doctor_name} on {date_str}. Available times include: {', '.join(doctor_slots[:5])}" + (f" and {len(doctor_slots) - 5} more" if len(doctor_slots) > 5 else "") + ". Please select one of these times."
                    else:
                        # No slots at all for this doctor on this date
                        available_dates = context.get("available_dates", [])
                        if available_dates:
                            response = f"I'm sorry, but {doctor_name} has no available slots on {date_str}. Here are the available dates:\n\n"
                            for date_info in available_dates:
                                response += f"📅 {date_info['formatted_date']}:\n"
                                
                                # Group time slots by morning/afternoon
                                morning_slots = [slot for slot in date_info['slots'] if "AM" in slot]
                                afternoon_slots = [slot for slot in date_info['slots'] if "PM" in slot]
                                
                                if morning_slots:
                                    response += f"Morning: • {' • '.join(morning_slots)}\n"
                                
                                if afternoon_slots:
                                    response += f"Afternoon: • {' • '.join(afternoon_slots)}\n"
                                
                                response += "\n"
                            state["response"] = response
                        else:
                            state["response"] = f"I'm sorry, but {doctor_name} has no available slots on {date_str}. Please select a different date."
            else:
                # Couldn't extract date or time
                state["response"] = date_time_result.get("message", "I couldn't understand the date and time you specified. Please try again with a clear date and time.")
        
        elif current_state == STATES["RESCHEDULING_CONFIRMING"]:
            # Check if user confirms
            confirmation = "yes" in transcript.lower() or "confirm" in transcript.lower() or "correct" in transcript.lower()
            
            if confirmation:
                try:
                    # Get necessary information from context
                    appointment_id = context["reschedule_appointment_id"]
                    new_date = context["new_appointment_date"]
                    new_time = context["new_appointment_time"]
                    
                    # Reschedule the appointment
                    success = Appointment.reschedule(appointment_id, new_date, new_time)
                    
                    if success:
                        # Format dates for display
                        new_formatted_date = datetime.datetime.strptime(new_date, "%Y-%m-%d").strftime("%A, %B %d, %Y")
                        doctor_name = context["reschedule_appointment"]["doctor_name"]
                        patient_name = context["reschedule_appointment"]["patient_name"]
                        
                        # Try to get patient email for notification
                        patient_email = None
                        try:
                            # Get the appointment to find the patient
                            appointment = Appointment.find_by_appointment_id(appointment_id)
                            if appointment and appointment.get("patient_id"):
                                # Look up the patient to get their email
                                patient = patients_collection.find_one({"_id": appointment["patient_id"]})
                                if patient and patient.get("email"):
                                    patient_email = patient["email"]
                                    debug_log(f"Found patient email for rescheduling notification: {patient_email}")
                        except Exception as e:
                            debug_log(f"Error retrieving patient email: {e}")
                        
                        # Update the intent to indicate rescheduling
                        state["intent"] = "reschedule_appointment"
                        
                        # Store rescheduling details for notification
                        reschedule_details = {
                            "appointment_id": appointment_id,
                            "patient_name": patient_name,
                            "patient_email": patient_email,
                            "doctor_name": doctor_name,
                            "old_date": context["reschedule_appointment"]["date"],
                            "old_time": context["reschedule_appointment"]["time"],
                            "new_date": new_date,
                            "new_time": new_time,
                            "formatted_new_date": new_formatted_date
                        }
                        
                        # Add to state for notification agent
                        state["reschedule_details"] = reschedule_details
                        
                        # Add to appointment_context for persistence
                        if "appointment_context" not in state:
                            state["appointment_context"] = {}
                        state["appointment_context"]["reschedule_details"] = reschedule_details
                        
                        # Success response
                        state["response"] = f"Great! I've rescheduled your appointment with {doctor_name} to {new_formatted_date} at {new_time}. A confirmation email will be sent to you. Is there anything else I can help you with today?"
                        
                        # Change state to RESCHEDULE_CONFIRMED instead of INITIAL
                        context["state"] = STATES["RESCHEDULE_CONFIRMED"]
                    else:
                        state["response"] = "I'm sorry, but I couldn't reschedule your appointment. Please call our office for assistance."
                except Exception as e:
                    debug_log(f"Error rescheduling appointment: {e}")
                    state["response"] = "I encountered an error while trying to reschedule your appointment. Please try again or contact our office directly."
                    context["state"] = STATES["INITIAL"]
            else:
                # User didn't confirm, go back to date/time collection
                state["response"] = "No problem. Please provide a different date and time for your appointment."
                context["state"] = STATES["RESCHEDULING_DATE_TIME"]
        
        elif current_state == STATES["COLLECTING_NAME"]:
            # Extract name from transcript
            debug_log(f"Processing name collection from transcript: '{transcript}'")
            
            # When responding to a direct name question, assume the entire response is likely a name
            # This is particularly important for simple responses like "John Smith" or "Tharushka Dinujaya"
            if len(transcript.split()) <= 4 and all(word[0].isalpha() for word in transcript.split()):
                debug_log("Input appears to be a direct name response")
                name = transcript.strip().title()
                debug_log(f"Using direct input as name: '{name}'")
            else:
                # Try the normal extraction for more complex inputs
                name = extract_name(transcript)
                debug_log(f"Extracted name via normal process: {name}")
            
            if name:
                context["patient_name"] = name
                context["state"] = STATES["COLLECTING_PHONE"]
                context["attempts"]["name"] = 0  # Reset attempts counter
                try:
                    state["response"] = get_step_prompt("collecting_phone", {"patient_name": name})
                    debug_log(f"Created phone collection prompt with name: '{name}'")
                except Exception as e:
                    debug_log(f"Error formatting phone prompt: {e}")
                    # Safe fallback to ensure we don't show an error message
                    state["response"] = f"Thank you, {name}. Could you please provide your phone number?"
            else:
                # Increment attempt counter
                context["attempts"]["name"] = context["attempts"].get("name", 0) + 1
                
                # If we reach max attempts or the input is very simple (likely just a name)
                if context["attempts"]["name"] >= 2 or len(transcript.split()) <= 4:
                    debug_log("Using transcript as fallback for name")
                    # Use a cleaned version of the transcript as a fallback
                    name = re.sub(r'^\s*(my name is|i am|this is|i\'m)\s+', '', transcript.lower())
                    name = name.strip().title()
                    
                    # If still empty after cleaning, use original transcript
                    if not name:
                        name = transcript.strip().title()
                    
                    debug_log(f"Fallback name: {name}")
                    context["patient_name"] = name if name else "Unknown Patient"
                    context["state"] = STATES["COLLECTING_PHONE"]
                    try:
                        state["response"] = get_step_prompt("collecting_phone", {"patient_name": name})
                    except Exception as e:
                        debug_log(f"Error formatting phone prompt for fallback: {e}")
                        state["response"] = f"Thank you, {name}. Could you please provide your phone number?"
                else:
                    state["response"] = get_step_prompt("collecting_repeat_name")
        
        elif current_state == STATES["COLLECTING_PHONE"]:
            # Extract phone from transcript
            debug_log(f"Processing phone collection from transcript: '{transcript}'")
            phone = extract_phone(transcript)
            debug_log(f"Extracted phone: {phone}")
            
            if phone:
                context["patient_phone"] = phone
                context["state"] = STATES["COLLECTING_BIRTHDATE"]
                context["attempts"]["phone"] = 0  # Reset attempts counter
                try:
                    state["response"] = get_step_prompt("collecting_birthdate")
                except Exception as e:
                    debug_log(f"Error formatting birthdate prompt: {e}")
                    state["response"] = "Thank you. Now, could you please share your date of birth in YYYY-MM-DD format?"
            else:
                # Increment attempt counter
                context["attempts"]["phone"] = context["attempts"].get("phone", 0) + 1
                
                # Single letter inputs are almost certainly not phone numbers
                if len(transcript.strip()) <= 1:
                    debug_log("Input too short to be a phone number")
                    try:
                        state["response"] = get_step_prompt("collecting_repeat_phone")
                    except Exception as e:
                        debug_log(f"Error formatting repeat phone prompt: {e}")
                        state["response"] = "I need a valid phone number with at least 10 digits. Could you please provide it?"
                # If too many failed attempts, try to move forward anyway
                elif context["attempts"]["phone"] >= 3:
                    debug_log("Max attempts reached for phone, using placeholder")
                    context["patient_phone"] = "000-000-0000"  # Placeholder
                    context["state"] = STATES["COLLECTING_BIRTHDATE"]
                    try:
                        state["response"] = get_step_prompt("collecting_birthdate")
                    except Exception as e:
                        debug_log(f"Error formatting birthdate prompt after max attempts: {e}")
                        state["response"] = "Thank you. Now, could you please share your date of birth in YYYY-MM-DD format?"
                else:
                    try:
                        state["response"] = get_step_prompt("collecting_repeat_phone")
                    except Exception as e:
                        debug_log(f"Error formatting repeat phone prompt: {e}")
                        state["response"] = "I need a valid phone number with at least 10 digits. Could you please provide it?"
        
        elif current_state == STATES["COLLECTING_BIRTHDATE"]:
            # Extract birthdate from transcript
            debug_log(f"Processing birthdate collection from transcript: '{transcript}'")
            birthdate = extract_birthdate(transcript)
            debug_log(f"Extracted birthdate: {birthdate}")
            
            if birthdate and validate_birthdate(birthdate):
                context["patient_birthdate"] = birthdate
                context["state"] = STATES["COLLECTING_REASON"]
                context["attempts"]["birthdate"] = 0  # Reset attempts counter
                state["response"] = get_step_prompt("collecting_reason")
            else:
                # Increment attempt counter
                context["attempts"]["birthdate"] = context["attempts"].get("birthdate", 0) + 1
                
                # If too many failed attempts, try to move forward anyway
                if context["attempts"]["birthdate"] >= 3:
                    debug_log("Max attempts reached for birthdate, using placeholder")
                    context["patient_birthdate"] = "1980-01-01"  # Default placeholder
                    context["state"] = STATES["COLLECTING_REASON"]
                    state["response"] = get_step_prompt("collecting_reason")
                else:
                    state["response"] = get_step_prompt("collecting_repeat_birthdate")
        
        elif current_state == STATES["COLLECTING_REASON"]:
            # Extract reason from transcript
            debug_log(f"Processing reason collection from transcript: '{transcript}'")
            reason = extract_reason(transcript)
            debug_log(f"Extracted reason: {reason}")
            
            if reason:
                context["appointment_reason"] = reason
                
                # Determine the specialty based on the reason
                specialty = Doctor.get_specialty_for_reason(reason)
                context["doctor_specialty"] = specialty
                context["state"] = STATES["SUGGESTING_SPECIALTY"]
                
                state["response"] = f"Based on your reason '{reason}', I recommend seeing a {specialty}. Would you like to proceed with this specialist, or would you prefer a different type of doctor?"
            else:
                # Increment attempt counter
                context["attempts"]["reason"] = context["attempts"].get("reason", 0) + 1
                
                # If too many failed attempts, try to move forward with a generic reason
                if context["attempts"]["reason"] >= 3:
                    debug_log("Max attempts reached for reason, using placeholder")
                    context["appointment_reason"] = "general consultation"
                    specialty = "Primary Care Physician"
                    context["doctor_specialty"] = specialty
                    context["state"] = STATES["SUGGESTING_SPECIALTY"]
                    state["response"] = f"I'll book you for a general consultation with a {specialty}. Would you like to proceed with this specialist, or would you prefer a different type of doctor?"
                else:
                    state["response"] = "I need to know the reason for your visit to match you with the right doctor. Could you please provide more details?"
        
        elif current_state == STATES["SUGGESTING_SPECIALTY"]:
            # Check if user agrees with the suggested specialty
            debug_log(f"Processing specialty confirmation from transcript: '{transcript}'")
            agreement_indicators = ["yes", "sure", "okay", "proceed", "that's fine", "sounds good"]
            disagreement_indicators = ["no", "different", "other", "change", "another", "not that"]
            
            # Default to agreement if no clear indication
            user_agrees = True
            
            for indicator in disagreement_indicators:
                if indicator in transcript.lower():
                    user_agrees = False
                    break
            
            debug_log(f"User agrees with specialty: {user_agrees}")
            
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
                debug_log(f"Changed specialty to: {specialty}")
            
            # Find doctors of this specialty
            try:
                doctors = Doctor.find_by_specialty(context["doctor_specialty"])
                debug_log(f"Found {len(doctors)} doctors with specialty {context['doctor_specialty']}")
            except Exception as e:
                debug_log(f"Error finding doctors: {e}")
                doctors = []
            
            if not doctors:
                state["response"] = f"I'm sorry, but we don't have any {context['doctor_specialty']} available at the moment. Would you like to see a General Practitioner instead?"
                context["doctor_specialty"] = "General Practitioner"
            else:
                # Select the first doctor for demo purposes
                # In a real app, you would let the user choose
                context["selected_doctor_id"] = str(doctors[0]["_id"])  # Convert ObjectId to string
                context["state"] = STATES["COLLECTING_DATE_TIME"]
                
                # Get available dates for this doctor
                available_dates = []
                available_dates_with_slots = []
                
                for date in doctors[0]["available_slots"]:
                    if doctors[0]["available_slots"][date]:  # Check if there are slots available
                        formatted_date = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%A, %B %d, %Y")
                        available_dates.append(formatted_date)
                        
                        # Get the actual time slots for this date
                        doctor_slots = get_doctor_available_slots(str(doctors[0]["_id"]), date)
                        
                        available_dates_with_slots.append({
                            "date": date,
                            "formatted_date": formatted_date,
                            "slots": doctor_slots
                        })
                
                # Store in context for later use
                context["available_dates"] = available_dates_with_slots[:3]  # Limit to 3 dates
                
                # Format dates for the initial response
                dates_str = ", ".join(available_dates[:3])  # Limit to 3 dates for simplicity
                
                # Create response with both dates and time slots
                response = f"I've assigned you to {doctors[0]['name']}, {context['doctor_specialty']}. When would you like to schedule your appointment? We have availability on {dates_str}.\n\n"
                
                # Add time slots information
                response += "Here are the available time slots:\n"
                
                for date_info in available_dates_with_slots[:3]:
                    response += f"\n📅 {date_info['formatted_date']}:\n"
                    
                    # Group time slots by morning/afternoon
                    morning_slots = [slot for slot in date_info['slots'] if "AM" in slot]
                    afternoon_slots = [slot for slot in date_info['slots'] if "PM" in slot]
                    
                    if morning_slots:
                        response += f"Morning: • {' • '.join(morning_slots)}\n"
                    
                    if afternoon_slots:
                        response += f"Afternoon: • {' • '.join(afternoon_slots)}\n"
                
                state["response"] = response
        
        elif current_state == STATES["COLLECTING_DATE_TIME"]:
            # Extract date and time from transcript using GPT
            debug_log(f"Processing date/time collection from transcript: '{transcript}'")
            
            # Get the doctor information
            doctor_id = context.get("selected_doctor_id")
            
            try:
                doctor = next((d for d in Doctor.find_by_specialty(context["doctor_specialty"]) 
                              if str(d["_id"]) == str(doctor_id)), None)
                debug_log(f"Found doctor: {doctor['name'] if doctor else None}")
                doctor_name = doctor["name"] if doctor else "the doctor"
            except Exception as e:
                debug_log(f"Error finding doctor: {e}")
                doctor = None
                doctor_name = "the doctor"
                
            # Use the improved date/time extraction
            date_time_result = extract_date_time_action(transcript)
            debug_log(f"Date time extraction result: {date_time_result}")
            
            # Special case: If we got a date but need time
            if not date_time_result.get("success") and date_time_result.get("need_time") and date_time_result.get("date"):
                # Store the date for later use
                date_str = date_time_result["date"]
                
                # Get the available slots for this date to show to the user
                if doctor:
                    # BUGFIX: Check if this date exists in the doctor's schedule first
                    doctor_obj = doctors_collection.find_one({"_id": ObjectId(doctor_id)})
                    if not doctor_obj or 'available_slots' not in doctor_obj or date_str not in doctor_obj['available_slots']:
                        state["response"] = f"I'm sorry, but {doctor_name} is not available on {parser.parse(date_str).strftime('%A, %B %d, %Y')}. Please select a different date from their available schedule."
                        return state
                        
                    doctor_slots = get_doctor_available_slots(doctor_id, date_str)
                    
                    if doctor_slots:
                        formatted_date = parser.parse(date_str).strftime('%A, %B %d, %Y')
                        
                        # Group times into morning and afternoon
                        morning_slots = [slot for slot in doctor_slots if "AM" in slot]
                        afternoon_slots = [slot for slot in doctor_slots if "PM" in slot]
                        
                        response = f"For {formatted_date}, we have the following appointment times available with {doctor_name}:\n\n"
                        
                        if morning_slots:
                            response += f"Morning: • {' • '.join(morning_slots)}\n"
                        
                        if afternoon_slots:
                            response += f"Afternoon: • {' • '.join(afternoon_slots)}\n"
                        
                        response += "\nPlease select a time for your appointment."
                        state["response"] = response
                    else:
                        state["response"] = f"I'm sorry, but there are no available slots on {parser.parse(date_str).strftime('%A, %B %d, %Y')} with {doctor_name}. Please select a different date."
                else:
                    state["response"] = "I'm sorry, there was an issue finding the doctor's available slots. Please try again with a different date."
                
                return state
            
            # If we have both date and time successfully extracted
            if date_time_result.get("success"):
                date_str = date_time_result["date"]
                time_str = date_time_result["time"]
                
                if not doctor:
                    state["response"] = "I'm sorry, there was an issue with the selected doctor. Let's start over."
                    context["state"] = STATES["INITIAL"]
                    return state
                
                # Check if slot is available
                doctor_slots = get_doctor_available_slots(doctor_id, date_str)
                
                if time_str in doctor_slots:
                    # We found a valid slot - save it for confirmation
                    context["appointment_date"] = date_str
                    context["appointment_time"] = time_str
                    
                    # Move to email collection
                    context["state"] = STATES["COLLECTING_EMAIL"]
                    
                    state["response"] = "Great! Now, please provide your email address for the appointment confirmation."
                else:
                    # Time not available for this doctor
                    if doctor_slots:
                        state["response"] = f"I'm sorry, but {time_str} is not available with {doctor_name} on {date_str}. Available times include: {', '.join(doctor_slots[:5])}" + (f" and {len(doctor_slots) - 5} more" if len(doctor_slots) > 5 else "") + ". Please select one of these times."
                    else:
                        # No slots at all for this doctor on this date
                        available_dates = context.get("available_dates", [])
                        if available_dates:
                            response = f"I'm sorry, but {doctor_name} has no available slots on {date_str}. Here are the available dates:\n\n"
                            for date_info in available_dates:
                                response += f"📅 {date_info['formatted_date']}:\n"
                                
                                # Group time slots by morning/afternoon
                                morning_slots = [slot for slot in date_info['slots'] if "AM" in slot]
                                afternoon_slots = [slot for slot in date_info['slots'] if "PM" in slot]
                                
                                if morning_slots:
                                    response += f"Morning: • {' • '.join(morning_slots)}\n"
                                
                                if afternoon_slots:
                                    response += f"Afternoon: • {' • '.join(afternoon_slots)}\n"
                                
                                response += "\n"
                            state["response"] = response
                        else:
                            state["response"] = f"I'm sorry, but {doctor_name} has no available slots on {date_str}. Please select a different date."
            else:
                # Couldn't extract date or time
                state["response"] = date_time_result.get("message", "I couldn't understand the date and time you specified. Please try again with a clear date and time, like 'March 15, 2025 at 2:00 PM'.")
        
        elif current_state == STATES["COLLECTING_EMAIL"]:
            # Extract email from transcript
            debug_log(f"Processing email collection from transcript: '{transcript}'")
            email = extract_email(transcript)
            debug_log(f"Extracted email: {email}")
            
            if email:
                context["patient_email"] = email
                context["state"] = STATES["CONFIRMING"]
                
                # Format date for display
                formatted_date = datetime.datetime.strptime(context["appointment_date"], "%Y-%m-%d").strftime("%A, %B %d, %Y")
                
                # Get doctor info
                try:
                    doctor = next((d for d in Doctor.find_by_specialty(context["doctor_specialty"]) 
                                  if str(d["_id"]) == str(context["selected_doctor_id"])), None)
                    debug_log(f"Found doctor for confirmation: {doctor['name'] if doctor else None}")
                except Exception as e:
                    debug_log(f"Error finding doctor for confirmation: {e}")
                    doctor = {'name': 'Unknown Doctor', 'specialty': context["doctor_specialty"]}
                
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
        
        elif current_state == STATES["CONFIRMING"]:
            # Check if user confirms
            debug_log(f"Processing confirmation from transcript: '{transcript}'")
            confirmation = "yes" in transcript.lower() or "confirm" in transcript.lower() or "correct" in transcript.lower()
            debug_log(f"User confirmed: {confirmation}")
            
            if confirmation:
                try:
                    # Save patient information
                    debug_log(f"Attempting to create patient with: name={context['patient_name']}, phone={context['patient_phone']}, email={context['patient_email']}, birthdate={context['patient_birthdate']}")
                    patient_id = Patient.create(
                        name=context["patient_name"],
                        phone=context["patient_phone"],
                        email=context["patient_email"],
                        birthdate=context["patient_birthdate"]
                    )
                    debug_log(f"Created patient with ID: {patient_id}")
                    
                    # Book the appointment
                    debug_log(f"Attempting to create appointment with: patient_id={patient_id}, doctor_id={context['selected_doctor_id']}, date={context['appointment_date']}, time={context['appointment_time']}, reason={context['appointment_reason']}")
                    appointment_result = Appointment.create(
                        patient_id=patient_id,
                        doctor_id=context["selected_doctor_id"],
                        date=context["appointment_date"],
                        time=context["appointment_time"],
                        reason=context["appointment_reason"]
                    )
                    appointment_id = appointment_result["appointment_id"]
                    db_id = appointment_result["db_id"]
                    debug_log(f"Created appointment with ID: {appointment_id} (DB ID: {db_id})")
                    
                    # Format date for display
                    formatted_date = datetime.datetime.strptime(context["appointment_date"], "%Y-%m-%d").strftime("%A, %B %d, %Y")
                    
                    # Get doctor info
                    doctor = next((d for d in Doctor.find_by_specialty(context["doctor_specialty"]) 
                                  if str(d["_id"]) == str(context["selected_doctor_id"])), None)
                    
                    # Change state to BOOKING_CONFIRMED instead of COMPLETED
                    context["state"] = STATES["BOOKING_CONFIRMED"]
                    
                    # Success response with appointment ID
                    state["response"] = f"Great! I've booked your appointment with {doctor['name']} for {formatted_date} at {context['appointment_time']}. Your appointment ID is {appointment_id}. A confirmation email has been sent to {context['patient_email']}. Please arrive 15 minutes early to complete any necessary paperwork."
                    
                    # Store appointment details in state for notification agent
                    state["appointment_details"] = {
                        "appointment_id": appointment_id,
                        "patient_name": context["patient_name"],
                        "patient_email": context["patient_email"],
                        "doctor_name": doctor["name"],
                        "doctor_specialty": context["doctor_specialty"],
                        "date": context["appointment_date"],
                        "formatted_date": formatted_date,
                        "time": context["appointment_time"],
                        "reason": context["appointment_reason"]
                    }
                except Exception as e:
                    debug_log(f"Error creating appointment: {str(e)}")
                    debug_log(f"Current context: {context}")
                    
                    # Try to continue anyway instead of showing an error
                    # First check if we already created the patient
                    try:
                        if patient_id:
                            # We got this far, so try scheduling appointment anyway
                            debug_log("Patient was created but appointment failed - trying again with simplified approach")
                            
                            try:
                                appointment_result = Appointment.create(
                                    patient_id=patient_id,
                                    doctor_id=context["selected_doctor_id"],
                                    date=context["appointment_date"],
                                    time=context["appointment_time"],
                                    reason=context["appointment_reason"]
                                )
                                appointment_id = appointment_result["appointment_id"]
                                
                                # Format date for display
                                formatted_date = datetime.datetime.strptime(context["appointment_date"], "%Y-%m-%d").strftime("%A, %B %d, %Y")
                                
                                context["state"] = STATES["BOOKING_CONFIRMED"]
                                state["response"] = f"Your appointment has been scheduled for {formatted_date} at {context['appointment_time']}. Your appointment ID is {appointment_id}."
                                return state
                            except Exception as inner_e:
                                debug_log(f"Second attempt at creating appointment failed: {str(inner_e)}")
                    except Exception as backup_e:
                        debug_log(f"Error in backup scheduling logic: {str(backup_e)}")
                    
                    # If we get here, all attempts failed
                    state["response"] = "I encountered an error while trying to book your appointment. Please try again later or contact our office directly."
                    context["state"] = STATES["INITIAL"]
            else:
                # Go back to initial state
                state["response"] = "No problem, let's start over with your appointment booking. What would you like to do?"
                context["state"] = STATES["INITIAL"]
        
        elif current_state == STATES["BOOKING_CONFIRMED"]:
            # Handle post-booking completion
            context["booking_complete"] = True
            
            # Check if we've already sent a notification
            if context.get("booking_notification_sent", False):
                debug_log("Booking notification already sent, not triggering again")
            else:
                # Mark for notification
                state["needs_notification"] = True
            
            # Check if the user says thanks or acknowledges completion
            acknowledgement_keywords = ["thank", "thanks", "great", "good", "excellent", "ok", "okay", "perfect", "bye", "goodbye"]
            
            if any(keyword in transcript.lower() for keyword in acknowledgement_keywords):
                # Reset appointment context to clear the booking flow
                context = {
                    "state": STATES["INITIAL"],
                    "booking_complete": True,
                    "last_completed_action": "booking",
                    # Preserve notification sent flag to prevent duplicates
                    "booking_notification_sent": context.get("booking_notification_sent", False)
                }
                
                # Set a response that transitions to general conversation
                state["response"] = "I'm here to help with anything else you might need. Feel free to ask about our services, doctors, or health information."
                
                # Update the intent to transition out of appointment flow
                state["intent"] = "general_inquiry"
                
                # Mark conversation as needing a context switch
                state["switch_context"] = True
            else:
                # For other inputs, provide general assistance
                state["response"] = "I'm here to help with your appointment. What would you like to do?"
        
        elif current_state == STATES["CANCELLATION_CONFIRMED"]:
            # Handle post-cancellation dialog
            context["cancellation_complete"] = True
            
            # Check if the user says thanks or acknowledges completion
            acknowledgement_keywords = ["thank", "thanks", "great", "good", "excellent", "ok", "okay", "perfect", "bye", "goodbye"]
            
            if any(keyword in transcript.lower() for keyword in acknowledgement_keywords):
                # Reset appointment context to clear the cancellation flow
                context = {
                    "state": STATES["INITIAL"],
                    "cancellation_complete": True,
                    "last_completed_action": "cancellation"
                }
                
                # Set a response that transitions to general conversation
                state["response"] = "I'm here to help with anything else you might need. Feel free to ask about our services, doctors, or health information."
                
                # Update the intent to transition out of appointment flow
                state["intent"] = "general_inquiry"
                
                # Mark conversation as needing a context switch
                state["switch_context"] = True
            else:
                # For other inputs after cancellation
                state["response"] = "I'm here to help if you need anything else. What would you like to do?"
        
        elif current_state == STATES["RESCHEDULE_CONFIRMED"]:
            # Handle post-rescheduling dialog
            context["reschedule_complete"] = True
            
            # Check if the user says thanks or acknowledges completion
            acknowledgement_keywords = ["thank", "thanks", "great", "good", "excellent", "ok", "okay", "perfect", "bye", "goodbye"]
            
            if any(keyword in transcript.lower() for keyword in acknowledgement_keywords):
                # Reset appointment context to clear the rescheduling flow
                context = {
                    "state": STATES["INITIAL"],
                    "reschedule_complete": True,
                    "last_completed_action": "rescheduling"
                }
                
                # Set a response that transitions to general conversation
                state["response"] = "I'm here to help with anything else you might need. Feel free to ask about our services, doctors, or health information."
                
                # Update the intent to transition out of appointment flow
                state["intent"] = "general_inquiry"
                
                # Mark conversation as needing a context switch
                state["switch_context"] = True
            else:
                # For other inputs after rescheduling
                state["response"] = "I'm here to help if you need anything else. What would you like to do?"
        
        else:
            # Default response for other states
            state["response"] = "I'm here to help with your appointment. What would you like to do?"
            context["state"] = STATES["INITIAL"]
        
        # Make sure to store the updated context in the state
        debug_log(f"Saving appointment_context: {context}")
        state["appointment_context"] = context
        
        trace.update(status="success")
        
    except Exception as e:
        trace.update(status="error", error={"message": str(e)})
        debug_log(f"Error in appointment agent: {e}")
        
        # Check if we're in the middle of a state transition and already have key data
        # This will prevent showing error messages when we're actually making progress
        if "appointment_context" in state and state["appointment_context"].get("state") == STATES["COLLECTING_PHONE"] and state["appointment_context"].get("patient_name"):
            # We've already processed the name and are moving to phone collection
            patient_name = state["appointment_context"]["patient_name"]
            debug_log(f"Error recovery: Already processed name '{patient_name}', continuing to phone collection")
            # Use fixed string format instead of template formatting
            state["response"] = f"Thank you, {patient_name}. Could you please provide your phone number?"
            return state
        else:
            state["response"] = "I'm having trouble processing your appointment request. Please try again or contact our office directly."
    
    return state

# Test functions for local testing
def test_extractions():
    """Test the extraction functions with sample inputs"""
    # Test name extraction with regex only
    test_names = [
        "My name is John Smith",
        "I'm Alex Muske",
        "This is Sarah Johnson",
        "Jane Doe is my name",
        "Robert"
    ]
    
    print("Testing name extraction:")
    for test in test_names:
        # Try regex patterns only
        name_patterns = [
            r'(?:my name is|I am|I\'m|call me|it\'s|this is)\s+([A-Z][a-z]+(?:\s+[A-Za-z][a-z]+){0,3})',
            r'(?:this is|name\'s|I\'m)\s+([A-Z][a-z]+(?:\s+[A-Za-z][a-z]+){0,3})',
            r'([A-Z][a-z]+(?:\s+[A-Za-z][a-z]+){0,3})(?:\s+(?:here|speaking|is my name))',
            r'([A-Z][a-z]+(?:\s+[A-Za-z][a-z]+){0,3})',
            r'([A-Za-z][a-z]+(?:\s+[A-Za-z][a-z]+){0,3})'
        ]
        
        extracted = None
        for pattern in name_patterns:
            match = re.search(pattern, test)
            if match:
                extracted = match.group(1).strip()
                if len(extracted.split()) >= 2 or len(extracted) > 3:
                    break
        
        print(f"Input: '{test}' -> Extracted: '{extracted}'")
    
    # Test phone extraction with regex only
    test_phones = [
        "My phone number is 123-456-7890",
        "Call me at (077) 598-2859",
        "You can reach me at +44 7911 123456",
        "07759828590",
        "Phone: 555.123.4567"
    ]
    
    print("\nTesting phone extraction:")
    for test in test_phones:
        # Try regex patterns only
        phone_patterns = [
            r'\b(\d{3})[-.\s]?(\d{3})[-.\s]?(\d{4})\b',
            r'\b(\(\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4})\b',
            r'\b(\+\d{1,3})[-.\s]?(\d{1,4})[-.\s]?(\d{1,4})[-.\s]?(\d{1,9})\b',
            r'\b(\d{2,3})[-.\s]?(\d{2,4})[-.\s]?(\d{2,4})[-.\s]?(\d{2,4})\b',
            r'\b(\d{8,15})\b',
            r'\b(\d{3,5})[-.\s]?(\d{3,5})[-.\s]?(\d{3,5})\b',
            r'phone(?:[-.\s]?(?:number)?[-.\s]?(?:is)?)[-.\s:]*([+\d][-.,()\s\d]{7,25})',
            r'number(?:[-.\s]?(?:is)?)[-.\s:]*([+\d][-.,()\s\d]{7,25})',
            r'call(?:[-.\s]?(?:me)?)[-.\s:]*(?:at)?[-.\s:]*([+\d][-.,()\s\d]{7,25})'
        ]
        
        extracted = None
        for pattern in phone_patterns:
            matches = re.findall(pattern, test)
            if matches:
                longest_match = max(matches, key=len)
                if longest_match.startswith('+'):
                    phone = '+' + re.sub(r'\D', '', longest_match[1:])
                else:
                    phone = re.sub(r'\D', '', longest_match)
                
                if 7 <= len(phone) <= 15 or (phone.startswith('+') and 8 <= len(phone) <= 16):
                    extracted = phone
                    break
        
        print(f"Input: '{test}' -> Extracted: '{extracted}'")
    
    # Test birthdate extraction with regex only
    test_birthdates = [
        "I was born on 1980-01-15",
        "My birth date is January 15, 1980",
        "DOB: 01/15/1980",
        "15th of January, 1980",
        "15-01-1980"
    ]
    
    print("\nTesting birthdate extraction:")
    for test in test_birthdates:
        # Normalize the transcript
        normalized = test.lower().replace('/', '-').replace('.', '-')
        
        # Try regex patterns only
        date_patterns = [
            r'\b(19\d{2}|20\d{2})[-/\.](0?[1-9]|1[0-2])[-/\.](0?[1-9]|[12][0-9]|3[01])\b',
            r'\b(0?[1-9]|1[0-2])[-/\.](0?[1-9]|[12][0-9]|3[01])[-/\.](19\d{2}|20\d{2})\b',
            r'\b(0?[1-9]|[12][0-9]|3[01])[-/\.](0?[1-9]|1[0-2])[-/\.](19\d{2}|20\d{2})\b',
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+(0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?,?\s+(\d{4})\b',
            r'\b(0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?\s+(?:of\s+)?(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?,?\s+(\d{4})\b'
        ]
        
        month_to_num = {
            'january': '01', 'jan': '01',
            'february': '02', 'feb': '02',
            'march': '03', 'mar': '03',
            'april': '04', 'apr': '04',
            'may': '05',
            'june': '06', 'jun': '06',
            'july': '07', 'jul': '07',
            'august': '08', 'aug': '08',
            'september': '09', 'sep': '09', 'sept': '09',
            'october': '10', 'oct': '10',
            'november': '11', 'nov': '11',
            'december': '12', 'dec': '12'
        }
        
        extracted = None
        for pattern in date_patterns:
            match = re.search(pattern, normalized, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                if len(groups) == 3:
                    # Determine format type based on pattern
                    if pattern.startswith(r'\b(19\d{2}|20\d{2})'):  # YYYY-MM-DD
                        year, month, day = groups
                    elif pattern.startswith(r'\b(0?[1-9]|1[0-2])'):  # MM-DD-YYYY
                        month, day, year = groups
                    elif pattern.startswith(r'\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)'):  # Month DD, YYYY
                        month, day, year = groups
                    elif pattern.startswith(r'\b(0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?\s+(?:of\s+)?'):  # DD Month YYYY
                        day, month, year = groups
                    else:  # DD-MM-YYYY
                        day, month, year = groups
                    
                    # Convert to proper format
                    if isinstance(month, str) and month.lower() in month_to_num:  # Month is a name
                        month = month_to_num[month.lower()]
                    
                    # Ensure two digits for month and day
                    month = str(month).zfill(2)
                    day = str(day).zfill(2)
                    
                    extracted = f"{year}-{month}-{day}"
                    break
        
        print(f"Input: '{test}' -> Extracted: '{extracted}'")

if __name__ == "__main__":
    test_extractions() 
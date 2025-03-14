import os
import io
import tempfile
import re
from openai import OpenAI
from langfuse.client import Langfuse

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Langfuse for logging
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)

def debug_log(message):
    """Helper function to print debug messages"""
    print(f"DEBUG RECEPTIONIST: {message}")

def transcribe_audio(audio_file):
    """
    Transcribe audio file using OpenAI's Whisper API
    
    Args:
        audio_file: The audio file to transcribe
    
    Returns:
        str: The transcribed text
    """
    # Create a trace in Langfuse
    trace = langfuse.trace(
        name="audio_transcription",
        metadata={"file_type": audio_file.content_type}
    )
    
    try:
        # Read audio data
        audio_data = audio_file.read()
        
        # Create a temporary file with the correct extension
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
            temp_audio.write(audio_data)
            temp_audio_path = temp_audio.name
        
        # Transcribe with Whisper using the temporary file
        with open(temp_audio_path, 'rb') as audio:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio
            )
        
        # Create a span with metadata directly in the constructor
        trace.span(
            name="whisper_transcription", 
            metadata={"transcript_length": len(transcript.text)}
        )
        
        # Remove the temporary file
        os.unlink(temp_audio_path)
        
        trace.update(status="success")
        return transcript.text
    
    except Exception as e:
        trace.update(status="error", error={"message": str(e)})
        print(f"Error transcribing audio: {e}")
        return "Sorry, I couldn't understand the audio."

def detect_appointment_intent(transcript):
    """
    Check if a transcript contains words suggesting an appointment intent
    
    Args:
        transcript: The transcribed text from the user
    
    Returns:
        bool: True if appointment-related intent is detected, False otherwise
    """
    appointment_keywords = [
        'appointment', 'schedule', 'book', 'reserve', 'visit', 
        'doctor', 'clinic', 'consultation', 'checkup', 'check-up',
        'reschedule', 'cancel', 'change', 'see a doctor', 'medical',
        'meet with', 'consult', 'slot'
    ]
    
    # Check for time-related patterns which often indicate appointment booking
    time_patterns = [
        r'\d{1,2}\s*(?::|\.)\s*\d{2}',  # 2:30, 14:00, 2.30
        r'\d{1,2}\s*(?:am|pm|a\.m\.|p\.m\.)',  # 2pm, 2 pm, 2a.m., 2 p.m.
        r'(?:morning|afternoon|evening|night)',  # morning, afternoon, etc.
        r'(?:today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)'  # days
    ]
    
    # Convert transcript to lowercase for case-insensitive matching
    transcript_lower = transcript.lower()
    
    # Check for appointment keywords
    for keyword in appointment_keywords:
        if keyword in transcript_lower:
            debug_log(f"Appointment intent detected via keyword: {keyword}")
            return True
    
    # Check for time patterns
    for pattern in time_patterns:
        if re.search(pattern, transcript_lower):
            if any(word in transcript_lower for word in ['book', 'schedule', 'appointment', 'visit', 'see', 'doctor', 'clinic']):
                debug_log(f"Appointment intent detected via time pattern: {pattern}")
                return True
    
    return False

def process_query(transcript):
    """
    Process the transcript and identify the intent
    
    Args:
        transcript: The transcribed text from the user
    
    Returns:
        dict: A dictionary containing the intent and other details
    """
    debug_log(f"Processing transcript: '{transcript}'")
    
    # First, check for appointment intent directly to avoid misclassification
    if detect_appointment_intent(transcript):
        debug_log("Direct appointment intent detection succeeded")
        return "schedule_appointment"
    
    # Create a trace in Langfuse
    trace = langfuse.trace(
        name="intent_classification",
        metadata={"transcript": transcript}
    )
    
    try:
        system_prompt = """
        You are an AI assistant for a healthcare clinic. Your task is to identify the intent 
        of the patient's query and classify it into one of the following categories:
        
        1. schedule_appointment - If the patient wants to book, reschedule, or cancel an appointment,
           or mentions anything about meeting with a doctor or visiting the clinic at a specific time.
        2. general_inquiry - If the patient is asking about clinic hours, services, or general information.
        3. health_question - If the patient is asking about medical advice or symptoms.
        4. emergency - If the patient describes an emergency situation.
        5. other - For any other type of query.
        
        IMPORTANT: If the patient mentions anything about booking, scheduling, or needing an appointment,
        or if they mention a specific date or time in relation to seeing a doctor, ALWAYS classify as schedule_appointment.
        
        Respond with ONLY the intent category as a single word.
        """
        
        # Identify intent using GPT-4o
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ],
            temperature=0.1
        )
        
        intent = response.choices[0].message.content.strip().lower()
        debug_log(f"GPT intent classification result: {intent}")
        
        # Create a span with metadata directly in the constructor
        trace.span(
            name="gpt4_intent_classification",
            metadata={"detected_intent": intent}
        )
        
        trace.update(status="success")
        return intent
    
    except Exception as e:
        trace.update(status="error", error={"message": str(e)})
        debug_log(f"Error in intent classification: {str(e)}")
        # Return schedule_appointment as a fallback if the query has appointment-like keywords
        if "appointment" in transcript.lower() or "book" in transcript.lower() or "schedule" in transcript.lower():
            return "schedule_appointment"
        return "unknown"

def receptionist_agent(state):
    """
    The main Receptionist Agent function for LangGraph
    
    Args:
        state: The current state object from LangGraph
    
    Returns:
        dict: Updated state with intent and routing information
    """
    # Extract the transcript from the state
    transcript = state.get("transcript", "")
    
    debug_log(f"Receptionist agent received transcript: '{transcript}'")
    
    # Process the query to identify intent
    intent = process_query(transcript)
    
    debug_log(f"Final intent classification: {intent}")
    
    # Update the state with the intent
    state["intent"] = intent
    
    # Return the updated state
    return state 
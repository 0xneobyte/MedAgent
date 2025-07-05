import os
import io
import tempfile
import re
import logging
from openai import OpenAI
from langfuse import Langfuse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Langfuse for logging
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)

def transcribe_audio(audio_file):
    """
    Transcribe audio file using OpenAI's Whisper API
    
    Args:
        audio_file: The audio file to transcribe
    
    Returns:
        str: The transcribed text
    """
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
        
        # Remove the temporary file
        os.unlink(temp_audio_path)
        
        return transcript.text
    
    except Exception as e:
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
    # Convert to lowercase and strip punctuation for simple pattern matching
    text = transcript.lower()
    
    # Keywords related to appointment scheduling
    schedule_keywords = [
        'appoint', 'book', 'schedule', 'see a doctor', 'see the doctor', 
        'come in', 'visit', 'consultation', 'check-up', 'checkup'
    ]
    
    # Check for keywords in the text
    for keyword in schedule_keywords:
        if keyword in text:
            return True
    
    # Check for time- or date-related patterns
    date_time_patterns = [
        r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
        r'\b(tomorrow|today|next week)\b',
        r'\b\d{1,2}:\d{2}\b',  # time format like 9:30
        r'\b\d{1,2} (am|pm)\b',  # time format like 10 am
        r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b'
    ]
    
    for pattern in date_time_patterns:
        if re.search(pattern, text):
            return True
    
    return False

def detect_reschedule_intent(transcript):
    """
    Specifically check for rescheduling intent in the transcript
    
    Args:
        transcript: The transcribed text from the user
    
    Returns:
        bool: True if rescheduling intent is detected, False otherwise
    """
    # Convert to lowercase for easier matching
    text = transcript.lower()
    
    # Keywords specifically related to rescheduling
    reschedule_keywords = [
        'reschedule', 'change appointment', 'move appointment', 
        'change my appointment', 'move my appointment', 'change the time',
        'different time', 'different date', 'new time', 'new date', 
        'another time', 'another date', 'postpone'
    ]
    
    # Check for reschedule-specific keywords
    for keyword in reschedule_keywords:
        if keyword in text:
            return True
            
    # Check for intent that combines scheduling words with change words
    schedule_words = ['appointment', 'visit', 'meeting', 'consultation']
    change_words = ['change', 'move', 'switch', 'reschedule']
    
    for s_word in schedule_words:
        for c_word in change_words:
            if s_word in text and c_word in text:
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
    logger.info(f"Processing query for intent classification")
    
    # First, check for rescheduling intent specifically
    if detect_reschedule_intent(transcript):
        logger.info("Intent classified as reschedule_appointment via keyword detection")
        return "reschedule_appointment"
    
    # Then check for general appointment intent
    if detect_appointment_intent(transcript):
        logger.info("Intent classified as schedule_appointment via keyword detection")
        return "schedule_appointment"
    
    try:
        system_prompt = """
        You are an AI assistant for a healthcare clinic. Your task is to identify the intent 
        of the patient's query and classify it into one of the following categories:
        
        1. schedule_appointment - If the patient wants to book a new appointment
           or mentions anything about meeting with a doctor or visiting the clinic at a specific time.
        2. reschedule_appointment - If the patient wants to change, move, or reschedule an existing appointment.
        3. cancel_appointment - If the patient wants to cancel an existing appointment.
        4. general_inquiry - If the patient is asking about clinic hours, services, or general information.
        5. health_question - If the patient is asking about medical advice or symptoms.
        6. emergency - If the patient describes an emergency situation.
        7. other - For any other type of query.
        
        IMPORTANT DISTINCTIONS:
        - If they mention booking or scheduling a NEW appointment, classify as schedule_appointment
        - If they mention CHANGING or MOVING an EXISTING appointment, classify as reschedule_appointment
        - If they mention CANCELING an appointment, classify as cancel_appointment
        
        Respond with ONLY the intent category as a single word.
        """
        
        # Identify intent using GPT-4o
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript}
        ]
        
        # Create a Langfuse generation for proper cost tracking
        generation = langfuse.start_generation(
            name="intent_classification_gpt4",
            model="gpt-4o",
            input=messages,
            metadata={"temperature": 0.1, "max_tokens": 50}
        )
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.1,
            max_tokens=50
        )
        
        intent = response.choices[0].message.content.strip().lower()
        logger.info(f"Intent classified as '{intent}' via GPT-4o (tokens: {response.usage.total_tokens})")
        
        # Update generation with output and usage data for cost tracking
        generation.update(
            output=intent,
            usage_details={
                "input": response.usage.prompt_tokens,
                "output": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
        )
        
        # End the generation
        generation.end()
        
        return intent
    
    except Exception as e:
        logger.warning(f"GPT intent classification failed: {str(e)}, falling back to keyword detection")
        
        # Check for rescheduling keywords as a fallback
        if "reschedule" in transcript.lower() or "change appointment" in transcript.lower() or "move appointment" in transcript.lower():
            logger.info("Intent classified as reschedule_appointment via fallback")
            return "reschedule_appointment"
        # Check for cancellation keywords
        elif "cancel" in transcript.lower() or "cancelation" in transcript.lower():
            logger.info("Intent classified as cancel_appointment via fallback")
            return "cancel_appointment"
        # Return schedule_appointment as a fallback if the query has appointment-like keywords
        elif "appointment" in transcript.lower() or "book" in transcript.lower() or "schedule" in transcript.lower():
            logger.info("Intent classified as schedule_appointment via fallback")
            return "schedule_appointment"
        
        logger.warning("No specific intent detected, returning unknown")
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
    conversation_id = state.get("conversation_id", "unknown")
    
    logger.info(f"Receptionist Agent: Processing new request [ID: {conversation_id}]")
    
    # Process the query to identify intent
    intent = process_query(transcript)
    
    logger.info(f"Intent Classification Complete: '{intent}' -> Routing to appropriate agent")
    
    # Update the state with the intent
    state["intent"] = intent
    
    # Return the updated state
    return state 
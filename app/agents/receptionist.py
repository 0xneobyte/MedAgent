import os
import io
import tempfile
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

def process_query(transcript):
    """
    Process the transcript and identify the intent
    
    Args:
        transcript: The transcribed text from the user
    
    Returns:
        dict: A dictionary containing the intent and other details
    """
    # Create a trace in Langfuse
    trace = langfuse.trace(
        name="intent_classification",
        metadata={"transcript": transcript}
    )
    
    try:
        system_prompt = """
        You are an AI assistant for a healthcare clinic. Your task is to identify the intent 
        of the patient's query and classify it into one of the following categories:
        
        1. schedule_appointment - If the patient wants to book, reschedule, or cancel an appointment.
        2. general_inquiry - If the patient is asking about clinic hours, services, or general information.
        3. health_question - If the patient is asking about medical advice or symptoms.
        4. emergency - If the patient describes an emergency situation.
        5. other - For any other type of query.
        
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
        
        # Create a span with metadata directly in the constructor
        trace.span(
            name="gpt4_intent_classification",
            metadata={"detected_intent": intent}
        )
        
        trace.update(status="success")
        return intent
    
    except Exception as e:
        trace.update(status="error", error={"message": str(e)})
        print(f"Error processing query: {e}")
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
    
    # Process the query to identify intent
    intent = process_query(transcript)
    
    # Update the state with the intent
    state["intent"] = intent
    
    # Return the updated state
    return state 
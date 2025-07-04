import os
import json
import pickle
import time
import uuid
import logging
from flask import Flask, request, jsonify, render_template, redirect, url_for, Response
from flask_cors import CORS
from dotenv import load_dotenv
from app.agents.receptionist import transcribe_audio, process_query
from app.agents.langgraph_workflow import process_workflow
import requests

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret_key")

# Enable CORS with credentials support
CORS(app, 
     supports_credentials=True,
     resources={r"/*": {"origins": "*"}},
     methods=["GET", "POST", "OPTIONS"])

# In-memory conversation store that doesn't depend on sessions
CONVERSATION_STORE = {}

@app.route('/')
def index_redirect():
    """Redirect to a new conversation with a unique ID"""
    # Generate a new conversation ID
    conversation_id = str(uuid.uuid4())
    logger.info(f"New session started - Conversation ID: {conversation_id[:8]}")
    
    # Initialize the conversation store
    CONVERSATION_STORE[conversation_id] = {
        "conversation_in_progress": False,
        "original_intent": "",
        "appointment_context": {},
        "last_updated": time.time()
    }
    
    # Redirect to the conversation page
    return redirect(url_for('index', conversation_id=conversation_id))

@app.route('/conversation/<conversation_id>')
def index(conversation_id):
    """Render the main application page with a specific conversation ID"""
    # Initialize conversation if it doesn't exist
    if conversation_id not in CONVERSATION_STORE:
        CONVERSATION_STORE[conversation_id] = {
            "conversation_in_progress": False,
            "original_intent": "",
            "appointment_context": {},
            "last_updated": time.time()
        }
    
    logger.info(f"User interface loaded for session: {conversation_id[:8]}")
    return render_template('index.html', conversation_id=conversation_id)

@app.after_request
def after_request(response):
    """Add headers to every response"""
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

@app.route('/api/transcribe/<conversation_id>', methods=['POST'])
def handle_transcription(conversation_id):
    """Handle audio transcription using Whisper API"""
    logger.info(f"Audio transcription request received [ID: {conversation_id[:8]}]")
    
    if 'audio' not in request.files:
        logger.warning("Audio transcription failed: No audio file provided")
        return jsonify({"error": "No audio file provided"}), 400
    
    # Ensure the conversation exists
    if conversation_id not in CONVERSATION_STORE:
        CONVERSATION_STORE[conversation_id] = {
            "conversation_in_progress": False,
            "original_intent": "",
            "appointment_context": {},
            "last_updated": time.time()
        }
    
    # Get the current conversation state
    conversation = CONVERSATION_STORE[conversation_id]
    appointment_context = conversation.get("appointment_context", {})
    
    audio_file = request.files['audio']
    
    # Transcribe audio using Whisper
    transcript = transcribe_audio(audio_file)
    logger.info(f"Audio transcribed successfully: \"{transcript[:50]}...\"" if len(transcript) > 50 else f"Audio transcribed: \"{transcript}\"")
    
    # Process the query with LangGraph workflow
    try:
        # Initialize state with transcript and conversation ID
        initial_state = {
            "transcript": transcript, 
            "patient_id": "demo_patient",
            "conversation_id": conversation_id
        }
        
        # Add conversation state if conversation is in progress
        conversation_in_progress = conversation.get("conversation_in_progress", False)
        original_intent = conversation.get("original_intent", "")
        
        if conversation_in_progress:
            initial_state["conversation_in_progress"] = True
            initial_state["original_intent"] = original_intent
            logger.info(f"Continuing conversation with original intent: {original_intent}")
        
        # Always add appointment context if it exists
        if appointment_context:
            initial_state["appointment_context"] = appointment_context
        
        logger.info(f"Starting LangGraph workflow processing...")
        
        # Run the workflow with our wrapper function
        final_state = process_workflow(initial_state)
        
        # Update conversation store with the results
        CONVERSATION_STORE[conversation_id]["conversation_in_progress"] = final_state.get("conversation_in_progress", False)
        CONVERSATION_STORE[conversation_id]["original_intent"] = final_state.get("original_intent", "")
        CONVERSATION_STORE[conversation_id]["last_updated"] = time.time()
        
        # Make sure to capture any appointment_context updates from the workflow
        if "appointment_context" in final_state:
            CONVERSATION_STORE[conversation_id]["appointment_context"] = final_state["appointment_context"]
        
        logger.info(f"Workflow completed - Intent: {final_state.get('intent', 'unknown')}")
        
        # Return the response
        return jsonify({
            "transcript": transcript,
            "intent": final_state.get("intent", "unknown"),
            "response": final_state.get("response", "I'm not sure how to respond to that."),
            "conversation_id": conversation_id
        })
    except Exception as e:
        logger.error(f"Error processing audio request: {e}")
        import traceback
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        return jsonify({
            "transcript": transcript,
            "intent": "error",
            "response": "I'm sorry, but I encountered an error processing your request.",
            "conversation_id": conversation_id
        })

@app.route('/api/text/<conversation_id>', methods=['POST'])
def handle_text(conversation_id):
    """Handle text input directly without audio transcription"""
    logger.info(f"Text message received [ID: {conversation_id[:8]}]")
    
    # Get the text from the request
    data = request.json
    if not data or 'text' not in data:
        logger.warning("Text processing failed: No text provided")
        return jsonify({"error": "No text provided"}), 400
    
    text = data['text']
    logger.info(f"Processing text input: \"{text[:50]}...\"" if len(text) > 50 else f"Processing text: \"{text}\"")
    
    # Ensure the conversation exists
    if conversation_id not in CONVERSATION_STORE:
        CONVERSATION_STORE[conversation_id] = {
            "conversation_in_progress": False,
            "original_intent": "",
            "appointment_context": {},
            "last_updated": time.time()
        }
    
    # Get the current conversation state
    conversation = CONVERSATION_STORE[conversation_id]
    appointment_context = conversation.get("appointment_context", {})
    
    # Process the query with LangGraph workflow
    try:
        # Initialize state with text and conversation ID
        initial_state = {
            "transcript": text,  # Use the text as transcript
            "patient_id": "demo_patient",
            "conversation_id": conversation_id
        }
        
        # Add conversation state if conversation is in progress
        conversation_in_progress = conversation.get("conversation_in_progress", False)
        original_intent = conversation.get("original_intent", "")
        
        if conversation_in_progress:
            initial_state["conversation_in_progress"] = True
            initial_state["original_intent"] = original_intent
            logger.info(f"Continuing text conversation with original intent: {original_intent}")
        
        # Always add appointment context if it exists
        if appointment_context:
            initial_state["appointment_context"] = appointment_context
        
        logger.info(f"Starting LangGraph workflow for text input...")
        
        # Run the workflow with our wrapper function
        final_state = process_workflow(initial_state)
        
        # Update conversation store with the results
        CONVERSATION_STORE[conversation_id]["conversation_in_progress"] = final_state.get("conversation_in_progress", False)
        CONVERSATION_STORE[conversation_id]["original_intent"] = final_state.get("original_intent", "")
        CONVERSATION_STORE[conversation_id]["last_updated"] = time.time()
        
        # Make sure to capture any appointment_context updates from the workflow
        if "appointment_context" in final_state:
            CONVERSATION_STORE[conversation_id]["appointment_context"] = final_state["appointment_context"]
        
        logger.info(f"Text workflow completed - Intent: {final_state.get('intent', 'unknown')}")
        
        # Return the response
        return jsonify({
            "transcript": text,
            "intent": final_state.get("intent", "unknown"),
            "response": final_state.get("response", "I'm not sure how to respond to that."),
            "conversation_id": conversation_id
        })
    except Exception as e:
        logger.error(f"Error processing text request: {e}")
        import traceback
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        return jsonify({
            "transcript": text,
            "intent": "error",
            "response": "I'm sorry, but I encountered an error processing your request.",
            "conversation_id": conversation_id
        })

@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    """Handle text-to-speech conversion using ElevenLabs API"""
    logger.info(f"Text-to-speech request received")
    
    try:
        # Get data from request
        data = request.json
        if not data or 'text' not in data:
            logger.warning("TTS failed: No text provided")
            return jsonify({"error": "No text provided"}), 400
        
        text = data['text']
        logger.info(f"Converting to speech: \"{text[:30]}...\"" if len(text) > 30 else f"Converting: \"{text}\"")
        
        # ElevenLabs API configuration
        ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")
        # Default to "Rachel" voice if not specified
        voice_id = data.get('voice_id', "21m00Tcm4TlvDq8ikWAM") 
        
        # Check if API key is available
        if not ELEVEN_LABS_API_KEY:
            logger.error("ElevenLabs API key not configured")
            return jsonify({"error": "ElevenLabs API key not configured"}), 500
        
        # Prepare request to ElevenLabs API
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVEN_LABS_API_KEY
        }
        
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.75,
                "similarity_boost": 0.75
            }
        }
        
        logger.info(f"Requesting audio generation from ElevenLabs...")
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            logger.info(f"Audio successfully generated ({len(response.content)} bytes)")
            
            # Return the audio data as MP3
            return Response(
                response.content,
                mimetype="audio/mpeg"
            )
        else:
            logger.error(f"ElevenLabs API error: {response.status_code} - {response.text}")
            return jsonify({
                "error": f"Error from ElevenLabs API: {response.status_code}",
                "details": response.text
            }), response.status_code
            
    except Exception as e:
        logger.error(f"TTS endpoint error: {e}")
        import traceback
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/debug/<conversation_id>', methods=['GET'])
def debug_info(conversation_id):
    """Return debug information about a conversation"""
    if conversation_id not in CONVERSATION_STORE:
        return jsonify({"error": "Conversation not found"}), 404
    
    conversation = CONVERSATION_STORE[conversation_id]
    
    return jsonify({
        "conversation_id": conversation_id,
        "conversation_data": conversation,
        "active_conversations": list(CONVERSATION_STORE.keys()),
    })

@app.route('/reset/<conversation_id>', methods=['GET'])
def reset_conversation(conversation_id):
    """Reset a specific conversation"""
    if conversation_id in CONVERSATION_STORE:
        CONVERSATION_STORE[conversation_id] = {
            "conversation_in_progress": False,
            "original_intent": "",
            "appointment_context": {},
            "last_updated": time.time()
        }
    
    return jsonify({"success": True, "message": "Conversation reset successfully"})

# Cleanup old conversations periodically
@app.before_request
def cleanup_old_conversations():
    """Remove conversations that haven't been updated in a while"""
    current_time = time.time()
    to_remove = []
    
    for cid, conversation in CONVERSATION_STORE.items():
        if current_time - conversation.get("last_updated", 0) > 3600:  # 1 hour
            to_remove.append(cid)
    
    if to_remove:
        for cid in to_remove:
            CONVERSATION_STORE.pop(cid, None)
        logger.info(f"Cleaned up {len(to_remove)} expired conversation(s)")

if __name__ == '__main__':
    logger.info("Starting MedAgent AI Healthcare Assistant...")
    logger.info("Multi-Agent Architecture: Receptionist → [Appointment/CallCenter] → Content → Notification")
    logger.info("LangGraph Workflow | GPT-4o Intelligence | Whisper Transcription | ElevenLabs TTS")
    logger.info("Server starting on http://0.0.0.0:5001")
    app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False) 
import os
import json
import pickle
import time
import uuid
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv
from app.agents.receptionist import transcribe_audio, process_query
from app.agents.langgraph_workflow import process_workflow

# Load environment variables
load_dotenv()

# Define debug log function first
def debug_log(message):
    """Helper function to print debug messages"""
    print(f"DEBUG APP: {message}")

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
    debug_log(f"Generated new conversation ID: {conversation_id}")
    
    # Initialize the conversation store
    CONVERSATION_STORE[conversation_id] = {
        "conversation_in_progress": False,
        "original_intent": "",
        "appointment_context": {},
        "last_updated": time.time()
    }
    debug_log(f"Initialized new conversation store for ID: {conversation_id}")
    
    # Redirect to the conversation page
    return redirect(url_for('index', conversation_id=conversation_id))

@app.route('/conversation/<conversation_id>')
def index(conversation_id):
    """Render the main application page with a specific conversation ID"""
    debug_log(f"Accessing conversation: {conversation_id}")
    
    # Initialize conversation if it doesn't exist
    if conversation_id not in CONVERSATION_STORE:
        debug_log(f"Conversation ID not found, initializing: {conversation_id}")
        CONVERSATION_STORE[conversation_id] = {
            "conversation_in_progress": False,
            "original_intent": "",
            "appointment_context": {},
            "last_updated": time.time()
        }
    
    return render_template('index.html', conversation_id=conversation_id)

@app.after_request
def after_request(response):
    """Add headers to every response"""
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

@app.route('/api/transcribe/<conversation_id>', methods=['POST'])
def handle_transcription(conversation_id):
    """Handle audio transcription using Whisper API"""
    debug_log(f"Received request at /api/transcribe/{conversation_id}")
    
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    # Ensure the conversation exists
    if conversation_id not in CONVERSATION_STORE:
        debug_log(f"Conversation ID not found, initializing: {conversation_id}")
        CONVERSATION_STORE[conversation_id] = {
            "conversation_in_progress": False,
            "original_intent": "",
            "appointment_context": {},
            "last_updated": time.time()
        }
    
    # Get the current conversation state
    conversation = CONVERSATION_STORE[conversation_id]
    debug_log(f"Retrieved conversation: {json.dumps(conversation)}")
    
    # Check appointment context
    appointment_context = conversation.get("appointment_context", {})
    debug_log(f"Retrieved appointment_context: {json.dumps(appointment_context)}")
    
    audio_file = request.files['audio']
    
    # Transcribe audio using Whisper
    transcript = transcribe_audio(audio_file)
    debug_log(f"Transcribed text: '{transcript}'")
    
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
        
        debug_log(f"Conversation in progress: {conversation_in_progress}")
        debug_log(f"Original intent: {original_intent}")
        
        if conversation_in_progress:
            debug_log("Conversation is in progress, restoring state")
            initial_state["conversation_in_progress"] = True
            initial_state["original_intent"] = original_intent
        
        # Always add appointment context if it exists, even if it's empty
        if appointment_context:
            debug_log(f"Adding appointment_context to initial state: {json.dumps(appointment_context)}")
            initial_state["appointment_context"] = appointment_context
        else:
            debug_log("No appointment_context to add to initial state")
        
        debug_log(f"Final initial state: {json.dumps(initial_state)}")
        
        # Run the workflow with our wrapper function
        final_state = process_workflow(initial_state)
        debug_log(f"Received final state: {json.dumps(final_state)}")
        
        # Update conversation store with the results
        CONVERSATION_STORE[conversation_id]["conversation_in_progress"] = final_state.get("conversation_in_progress", False)
        CONVERSATION_STORE[conversation_id]["original_intent"] = final_state.get("original_intent", "")
        CONVERSATION_STORE[conversation_id]["last_updated"] = time.time()
        
        # Make sure to capture any appointment_context updates from the workflow
        if "appointment_context" in final_state:
            debug_log(f"Saving appointment_context to conversation store: {json.dumps(final_state['appointment_context'])}")
            CONVERSATION_STORE[conversation_id]["appointment_context"] = final_state["appointment_context"]
        else:
            debug_log("No appointment_context in final state to save")
            
        debug_log(f"Final conversation store state: {json.dumps(CONVERSATION_STORE[conversation_id])}")
        
        # Return the response
        return jsonify({
            "transcript": transcript,
            "intent": final_state.get("intent", "unknown"),
            "response": final_state.get("response", "I'm not sure how to respond to that."),
            "conversation_id": conversation_id
        })
    except Exception as e:
        debug_log(f"Error processing query: {e}")
        import traceback
        debug_log(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "transcript": transcript,
            "intent": "error",
            "response": "I'm sorry, but I encountered an error processing your request.",
            "conversation_id": conversation_id
        })

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
    
    for cid in to_remove:
        CONVERSATION_STORE.pop(cid, None)
        debug_log(f"Removed expired conversation: {cid}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False) 
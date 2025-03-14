import os
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from dotenv import load_dotenv
from app.agents.receptionist import transcribe_audio, process_query
from app.agents.langgraph_workflow import process_workflow

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret_key")
CORS(app)  # Enable CORS for all routes

# In-memory conversation store for demo purposes
# In production, this would be a database
conversation_store = {}

@app.route('/')
def index():
    """Render the main application page"""
    # Generate a session ID if one doesn't exist
    if 'session_id' not in session:
        session['session_id'] = os.urandom(16).hex()
    
    # Initialize conversation state for this session if needed
    if session['session_id'] not in conversation_store:
        conversation_store[session['session_id']] = {
            "conversation_in_progress": False,
            "original_intent": "",
            "appointment_context": {}
        }
    
    return render_template('index.html')

@app.route('/api/transcribe', methods=['POST'])
def handle_transcription():
    """Handle audio transcription using Whisper API"""
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    # Generate a session ID if one doesn't exist (for non-browser clients)
    if 'session_id' not in session:
        session['session_id'] = os.urandom(16).hex()
    
    # Get session ID
    session_id = session['session_id']
    
    # Initialize conversation state for this session if needed
    if session_id not in conversation_store:
        conversation_store[session_id] = {
            "conversation_in_progress": False,
            "original_intent": "",
            "appointment_context": {}
        }
    
    audio_file = request.files['audio']
    
    # Transcribe audio using Whisper
    transcript = transcribe_audio(audio_file)
    
    # Process the query with LangGraph workflow
    try:
        # Initialize state with transcript and existing conversation state
        initial_state = {"transcript": transcript, "patient_id": "demo_patient"}
        
        # Add conversation state if conversation is in progress
        if conversation_store[session_id]["conversation_in_progress"]:
            initial_state["conversation_in_progress"] = True
            initial_state["original_intent"] = conversation_store[session_id]["original_intent"]
        
        # If we have appointment context, add it
        if conversation_store[session_id].get("appointment_context"):
            initial_state["appointment_context"] = conversation_store[session_id]["appointment_context"]
        
        print(f"DEBUG APP: Processing with initial state: {initial_state}")
        
        # Run the workflow with our wrapper function
        final_state = process_workflow(initial_state)
        
        # Update conversation store with the results
        conversation_store[session_id]["conversation_in_progress"] = final_state.get("conversation_in_progress", False)
        conversation_store[session_id]["original_intent"] = final_state.get("original_intent", "")
        
        # Save appointment context if it exists
        if "appointment_context" in final_state:
            conversation_store[session_id]["appointment_context"] = final_state["appointment_context"]
        
        # Extract response from final state
        response = final_state.get("response", "I'm sorry, I couldn't process your request.")
        intent = final_state.get("intent", "unknown")
        
        return jsonify({
            "transcript": transcript,
            "intent": intent,
            "response": response
        })
    except Exception as e:
        print(f"Error processing query: {e}")
        return jsonify({
            "transcript": transcript,
            "intent": "error",
            "response": "I'm sorry, but I encountered an error processing your request."
        })

if __name__ == '__main__':
    app.run(debug=True) 
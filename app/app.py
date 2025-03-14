import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from app.agents.receptionist import transcribe_audio, process_query
from app.agents.langgraph_workflow import workflow

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/')
def index():
    """Render the main application page"""
    return render_template('index.html')

@app.route('/api/transcribe', methods=['POST'])
def handle_transcription():
    """Handle audio transcription using Whisper API"""
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files['audio']
    
    # Transcribe audio using Whisper
    transcript = transcribe_audio(audio_file)
    
    # Process the query with LangGraph workflow
    try:
        # Initialize state with transcript
        initial_state = {"transcript": transcript, "patient_id": "demo_patient"}
        
        # Run the workflow - in langgraph 0.3.1, we use invoke() instead of run()
        final_state = workflow.invoke(initial_state)
        
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
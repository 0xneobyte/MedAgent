# MedAgent: AI-Powered Healthcare Assistant

## Overview

MedAgent is an AI-powered multi-agent system designed to automate patient interactions, appointment scheduling, and notifications in healthcare settings. It integrates LangGraph for orchestrating multiple AI agents, LangFuse for monitoring and logging, OpenAI's Whisper for speech-to-text transcription, and GPT-4o for natural language understanding and response generation.

The system features a web-based interface where patients can speak into their microphone, have their speech transcribed, and receive voice responses from specialized AI agents that handle different types of queries.

## Key Features

- **Voice-based Interaction**: Uses Web Speech API for microphone input and text-to-speech output
- **Multi-Agent Architecture**: Different specialized agents handle different types of queries
- **Intent Classification**: Automatically determines what the patient needs
- **Appointment Management**: Schedule, reschedule, and cancel appointments
- **General Inquiries**: Answers common questions about clinic services, hours, etc.
- **Content Management**: Ensures responses comply with healthcare guidelines
- **Notification System**: Sends email confirmations for appointments

## System Architecture

The system follows an agentic flow where different agents interact to handle patient requests:

1. **AI Receptionist Agent**: Handles initial voice transcription and intent classification
2. **Appointment Management Agent**: Manages scheduling and calendar operations
3. **Call Center Agent**: Responds to general inquiries and FAQs
4. **Content Management Agent**: Validates responses for quality and compliance
5. **Notification Agent**: Handles email communications

## Technologies Used

- **LangGraph**: For structured multi-agent workflows
- **LangFuse**: For AI telemetry and monitoring
- **OpenAI Whisper**: For speech-to-text transcription
- **GPT-4o**: For natural language understanding
- **Web Speech API**: For microphone input and text-to-speech output
- **SendGrid**: For email communications
- **Flask**: For web application backend
- **MongoDB** (planned): For data persistence

## Setup Instructions

### Prerequisites

- Python 3.10+ installed
- OpenAI API key
- LangFuse account
- SendGrid account (optional for emails)

### Installation

#### Option 1: Using Conda (Recommended)

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/medagent.git
   cd medagent
   ```

2. Create and activate a new Conda environment:

   ```bash
   conda create -n medagent python=3.10
   conda activate medagent
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file from the template:

   ```bash
   cp .env.example .env
   ```

5. Edit the `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
   LANGFUSE_SECRET_KEY=your_langfuse_secret_key
   ```

#### Option 2: Using venv

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/medagent.git
   cd medagent
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file from the template:

   ```bash
   cp .env.example .env
   ```

5. Edit the `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
   LANGFUSE_SECRET_KEY=your_langfuse_secret_key
   ```

### Running the Application

1. Start the application:

   ```bash
   python run.py
   ```

2. Visit http://localhost:5000 in your web browser
3. Click the microphone button and speak your request
4. The AI will transcribe your speech, process your request, and respond both visually and verbally

## Demo Queries

Try these example queries to test different agent capabilities:

- "I'd like to schedule an appointment for next Friday at 2 PM"
- "What are your office hours?"
- "Do you accept insurance?"
- "I need to cancel my appointment"
- "Can you tell me about the services you offer?"

## For Hackathon Judges

This project demonstrates the power of agentic AI systems in healthcare, using:

1. **LangGraph**: Our system uses LangGraph to connect multiple specialized agents in a workflow, allowing for complex request handling and routing.
2. **LangFuse**: We've integrated LangFuse for comprehensive monitoring and logging of all AI interactions, enabling performance tracking and debugging.
3. **Innovative UI**: The voice-based interface creates a natural, accessible way for patients to interact with healthcare systems.

## Future Enhancements

- Integration with real calendaring systems
- Multilingual support
- More sophisticated appointment conflict resolution
- Advanced healthcare compliance checking
- SMS notifications
- Web-based appointment dashboard

## License

MIT

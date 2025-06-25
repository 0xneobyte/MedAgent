# MedAgent: AI Agentic Call Center Automation
## Software Instruction Document

**Version:** 1.0  
**Date:** June 25, 2025  
**Document Type:** User & Technical Manual  

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [System Requirements](#2-system-requirements)
3. [Installation Guide](#3-installation-guide)
4. [Configuration Setup](#4-configuration-setup)
5. [User Interface Guide](#5-user-interface-guide)
6. [Voice Interaction Instructions](#6-voice-interaction-instructions)
7. [Agent System Architecture](#7-agent-system-architecture)
8. [API Documentation](#8-api-documentation)
9. [Troubleshooting Guide](#9-troubleshooting-guide)
10. [Deployment Instructions](#10-deployment-instructions)
11. [Customization Guide](#11-customization-guide)
12. [Monitoring & Analytics](#12-monitoring--analytics)

---

## 1. System Overview

### 1.1 Introduction
MedAgent is an AI-powered multi-agent call center automation system designed to handle customer interactions through natural voice conversations. While demonstrated in a healthcare context, the system is designed as a plug-and-play solution adaptable to any industry.

### 1.2 Key Features
- **Voice-First Interface**: Natural speech input and output
- **Multi-Agent Architecture**: 5 specialized AI agents working in coordination
- **Real-Time Processing**: Instant response generation and intent classification
- **Industry Adaptable**: Configurable for different business domains
- **Comprehensive Monitoring**: Full conversation tracking and analytics
- **Scalable Deployment**: Docker containerization for easy scaling

### 1.3 Core Components
- **Frontend**: Voice-enabled web interface
- **Backend**: Flask application with multi-agent orchestration
- **AI Engine**: OpenAI GPT-4 with Whisper for speech processing
- **Workflow Management**: LangGraph for agent coordination
- **Monitoring**: LangFuse for AI telemetry and analytics
- **Notifications**: Email integration via SendGrid

---

## 2. System Requirements

### 2.1 Hardware Requirements
- **Minimum RAM**: 8 GB
- **Recommended RAM**: 16 GB or higher
- **CPU**: Multi-core processor (4+ cores recommended)
- **Storage**: 10 GB free space
- **Network**: Stable internet connection for API calls

### 2.2 Software Requirements
- **Python**: 3.10 or higher
- **Node.js**: 16.0 or higher (for development tools)
- **Operating System**: Windows 10+, macOS 10.15+, or Linux
- **Browser**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+

### 2.3 External Services
- **OpenAI API**: For GPT-4 and Whisper services
- **LangFuse**: For AI monitoring and analytics
- **SendGrid** (Optional): For email notifications
- **MongoDB** (Optional): For data persistence

---

## 3. Installation Guide

### 3.1 Local Development Setup

#### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd MedAgent-1
```

#### Step 2: Create Virtual Environment
```bash
# For macOS/Linux
python3 -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
venv\Scripts\activate
```

#### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 4: Environment Configuration
Create a `.env` file in the root directory:
```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# LangFuse Configuration
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com

# SendGrid Configuration (Optional)
SENDGRID_API_KEY=your_sendgrid_api_key
FROM_EMAIL=your_sender_email@example.com

# Flask Configuration
FLASK_SECRET_KEY=your_secret_key_here
FLASK_ENV=development
```

### 3.2 Docker Installation

#### Step 1: Build Docker Image
```bash
docker build -t medagent .
```

#### Step 2: Run with Docker Compose
```bash
docker-compose up -d
```

---

## 4. Configuration Setup

### 4.1 API Keys Configuration

#### OpenAI API Setup
1. Visit [OpenAI Platform](https://platform.openai.com)
2. Create an account or sign in
3. Navigate to API Keys section
4. Generate a new API key
5. Add to `.env` file as `OPENAI_API_KEY`

#### LangFuse Setup
1. Visit [LangFuse Cloud](https://cloud.langfuse.com)
2. Create a new project
3. Copy the public and secret keys
4. Add to `.env` file

### 4.2 Agent Configuration

#### Modifying Agent Behavior
Edit the following files to customize agent responses:

**Receptionist Agent** (`app/agents/receptionist.py`):
- Intent classification prompts
- Transcription settings
- Response templates

**Appointment Agent** (`app/agents/appointment.py`):
- Booking workflow states
- Validation rules
- Available time slots

**Call Center Agent** (`app/agents/call_center.py`):
- FAQ responses
- Company information
- General inquiry handling

### 4.3 Database Configuration

#### MongoDB Setup (Optional)
```python
# In app/models.py
MONGODB_URI = "mongodb://localhost:27017/medagent"
```

#### In-Memory Database (Default)
The system uses in-memory storage by default for demo purposes.

---

## 5. User Interface Guide

### 5.1 Starting the Application

#### Development Mode
```bash
python run.py
```

#### Production Mode
```bash
flask run --host=0.0.0.0 --port=5000
```

### 5.2 Accessing the Interface
1. Open web browser
2. Navigate to `http://localhost:5000`
3. Allow microphone permissions when prompted
4. The system will generate a unique conversation ID

### 5.3 Interface Elements

#### Main Screen Components
- **Microphone Button**: Click to start/stop voice recording
- **Conversation Display**: Shows the ongoing conversation
- **Status Indicators**: Visual feedback for system state
- **Settings Panel**: Access to configuration options

#### Visual States
- **Idle**: Blue gradient background
- **Listening**: Animated gradient with pulse effect
- **Processing**: Loading indicators
- **Responding**: Text-to-speech visual feedback

---

## 6. Voice Interaction Instructions

### 6.1 Basic Usage

#### Starting a Conversation
1. Click the microphone button or press spacebar
2. Wait for the "Listening..." indicator
3. Speak clearly into your microphone
4. The system will automatically detect when you stop speaking

#### Best Practices for Voice Input
- **Speak clearly** at normal conversational pace
- **Avoid background noise** when possible
- **Wait for responses** before speaking again
- **Use natural language** - no need for specific commands

### 6.2 Supported Interaction Types

#### Appointment Scheduling
**Example phrases:**
- "I'd like to schedule an appointment"
- "Book me a doctor's visit"
- "I need to see a doctor next week"

#### General Inquiries
**Example phrases:**
- "What are your office hours?"
- "Do you accept insurance?"
- "Where is your clinic located?"

#### Appointment Management
**Example phrases:**
- "I need to cancel my appointment"
- "Can I reschedule my visit?"
- "What time is my appointment?"

### 6.3 Conversation Flow

#### Typical Appointment Booking Flow
1. **Initial Request**: User expresses intent to schedule
2. **Information Gathering**: System collects:
   - Patient name
   - Phone number
   - Date of birth
   - Reason for visit
   - Preferred date/time
   - Email address
3. **Confirmation**: System summarizes and confirms details
4. **Completion**: Appointment confirmed and notification sent

---

## 7. Agent System Architecture

### 7.1 Multi-Agent Overview

#### Agent Hierarchy
```
┌─────────────────┐
│ Receptionist    │ ← Entry point for all interactions
│ Agent           │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Appointment     │    │ Call Center     │    │ Content Mgmt    │
│ Agent           │    │ Agent           │    │ Agent           │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  ▼
                    ┌─────────────────┐
                    │ Notification    │
                    │ Agent           │
                    └─────────────────┘
```

### 7.2 Agent Responsibilities

#### Receptionist Agent
- **Primary Function**: Intent classification and conversation routing
- **Key Features**:
  - Speech-to-text transcription using OpenAI Whisper
  - Intent detection using GPT-4
  - Conversation state management
  - Initial customer interaction

#### Appointment Agent
- **Primary Function**: Handle all appointment-related operations
- **Key Features**:
  - Multi-step booking workflow
  - Data validation and collection
  - Schedule management
  - Appointment modifications (cancel/reschedule)

#### Call Center Agent
- **Primary Function**: General customer service inquiries
- **Key Features**:
  - FAQ handling
  - Company information provision
  - General support queries
  - Escalation protocols

#### Content Management Agent
- **Primary Function**: Quality assurance and compliance
- **Key Features**:
  - Response validation
  - Compliance checking
  - Content filtering
  - Professional tone enforcement

#### Notification Agent
- **Primary Function**: Communication and alerts
- **Key Features**:
  - Email confirmations
  - SMS notifications (if configured)
  - Appointment reminders
  - System alerts

### 7.3 LangGraph Workflow

#### Workflow States
```python
class WorkflowState(TypedDict):
    transcript: str                    # User's spoken input
    intent: str                       # Classified intent
    patient_id: str                   # Patient identifier
    response: str                     # Agent response
    appointment_details: Dict[str, Any]  # Booking information
    conversation_in_progress: bool    # Conversation state
    original_intent: str             # Initial intent
    appointment_context: Dict[str, Any]  # Context data
```

#### Decision Flow
1. **Input Processing**: Receptionist receives and transcribes audio
2. **Intent Classification**: Determine user's intent
3. **Agent Routing**: Route to appropriate specialized agent
4. **Response Generation**: Generate contextual response
5. **Quality Check**: Content management validation
6. **Output Delivery**: Return response to user
7. **Notification Trigger**: Send confirmations if needed

---

## 8. API Documentation

### 8.1 REST API Endpoints

#### Voice Processing Endpoint
```http
POST /process_voice
Content-Type: multipart/form-data

Parameters:
- audio: Audio file (WAV, MP3, M4A)
- conversation_id: Unique conversation identifier

Response:
{
  "status": "success",
  "response": "Generated response text",
  "intent": "classified_intent",
  "audio_url": "/static/audio/response.mp3"
}
```

#### Conversation Management
```http
GET /<conversation_id>
Returns the conversation interface

POST /new_conversation
Creates a new conversation session

Response:
{
  "conversation_id": "uuid-string",
  "status": "initialized"
}
```

#### System Status
```http
GET /health
Returns system health status

Response:
{
  "status": "healthy",
  "agents": {
    "receptionist": "active",
    "appointment": "active",
    "call_center": "active",
    "content_management": "active",
    "notification": "active"
  },
  "services": {
    "openai": "connected",
    "langfuse": "connected"
  }
}
```

### 8.2 WebSocket Support (Future Enhancement)
Real-time bidirectional communication for live conversation updates.

---

## 9. Troubleshooting Guide

### 9.1 Common Issues

#### Microphone Not Working
**Symptoms**: No audio detection, "Microphone access denied"
**Solutions**:
1. Check browser microphone permissions
2. Ensure microphone is not used by other applications
3. Try refreshing the page and granting permissions again
4. Test microphone in other applications

#### Poor Speech Recognition
**Symptoms**: Incorrect transcriptions, no response to speech
**Solutions**:
1. Speak more clearly and slowly
2. Reduce background noise
3. Check microphone quality and position
4. Ensure stable internet connection
5. Try using Chrome browser for better Web Speech API support

#### API Connection Errors
**Symptoms**: "API Error", slow responses, timeout errors
**Solutions**:
1. Verify OpenAI API key is valid and has credits
2. Check internet connection stability
3. Verify LangFuse credentials
4. Check API rate limits
5. Review console logs for specific error messages

#### Agent Response Issues
**Symptoms**: Inappropriate responses, agent confusion
**Solutions**:
1. Check agent configuration files
2. Verify prompt templates are correct
3. Review conversation context and state
4. Check LangFuse logs for debugging
5. Restart the application to reset state

### 9.2 Debug Mode

#### Enabling Debug Logging
```python
# In app/app.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Console Debugging
Open browser developer tools (F12) to view:
- Speech recognition events
- API call responses
- Agent routing decisions
- Error messages and stack traces

### 9.3 Performance Optimization

#### Improving Response Time
1. **Use local Whisper model** for faster transcription
2. **Optimize prompts** to reduce token usage
3. **Implement caching** for common responses
4. **Use streaming responses** for real-time feedback

#### Memory Management
1. **Clear conversation history** periodically
2. **Limit conversation context** to recent messages
3. **Monitor memory usage** in production
4. **Implement session cleanup** for idle conversations

---

## 10. Deployment Instructions

### 10.1 Production Deployment

#### Docker Production Setup
```dockerfile
# Use production-ready image
FROM python:3.11-slim

# Set production environment
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Copy application
COPY . /app
WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 5000

# Run with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "run:app"]
```

#### Cloud Deployment Options

**AWS Deployment**:
```bash
# Using AWS ECS
aws ecs create-cluster --cluster-name medagent-cluster
aws ecs register-task-definition --cli-input-json file://task-definition.json
aws ecs create-service --cluster medagent-cluster --service-name medagent-service
```

**Google Cloud Deployment**:
```bash
# Using Google Cloud Run
gcloud run deploy medagent --image gcr.io/PROJECT_ID/medagent --platform managed
```

**Azure Deployment**:
```bash
# Using Azure Container Instances
az container create --resource-group myResourceGroup --name medagent --image medagent:latest
```

### 10.2 Environment Configuration

#### Production Environment Variables
```env
# Production settings
FLASK_ENV=production
DEBUG=False
TESTING=False

# Secure secret key
FLASK_SECRET_KEY=generate_strong_secret_key_here

# Production database
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/medagent

# Production monitoring
LANGFUSE_HOST=https://cloud.langfuse.com
ENABLE_MONITORING=true

# Security settings
CORS_ORIGINS=https://yourdomain.com
RATE_LIMIT_ENABLED=true
```

### 10.3 Security Considerations

#### API Security
1. **Rate Limiting**: Implement rate limiting for API endpoints
2. **CORS Configuration**: Restrict origins to trusted domains
3. **Input Validation**: Sanitize all user inputs
4. **API Key Protection**: Use environment variables for sensitive keys
5. **HTTPS Only**: Force HTTPS in production

#### Data Privacy
1. **Audio Data**: Implement automatic deletion of audio files
2. **Conversation Logs**: Set retention policies for conversation data
3. **PII Protection**: Mask or encrypt personally identifiable information
4. **Compliance**: Ensure HIPAA compliance for healthcare deployments

---

## 11. Customization Guide

### 11.1 Industry Adaptation

#### Creating New Industry Modules

**Step 1: Define Industry-Specific Intents**
```python
# In app/agents/receptionist.py
INDUSTRY_INTENTS = {
    "insurance": ["claim_inquiry", "policy_question", "coverage_check"],
    "banking": ["account_inquiry", "loan_application", "fraud_report"],
    "retail": ["order_status", "return_request", "product_info"]
}
```

**Step 2: Customize Agent Prompts**
```python
# Industry-specific prompt templates
INSURANCE_PROMPT = """
You are an AI assistant for an insurance company.
Help customers with:
- Policy inquiries
- Claim processing
- Coverage questions
- Payment issues
"""
```

**Step 3: Configure Workflow States**
```python
# Industry-specific state management
class InsuranceWorkflowState(TypedDict):
    policy_number: str
    claim_id: str
    coverage_type: str
    # ... other industry-specific fields
```

### 11.2 UI Customization

#### Brand Customization
```css
/* In app/templates/index.html */
:root {
    --primary-color: #your-brand-color;
    --secondary-color: #your-secondary-color;
    --logo-url: url('path/to/your/logo.png');
}
```

#### Language Support
```javascript
// Add language selection
const SUPPORTED_LANGUAGES = {
    'en-US': 'English',
    'es-ES': 'Spanish',
    'fr-FR': 'French',
    'de-DE': 'German'
};
```

### 11.3 Integration Templates

#### CRM Integration Example
```python
class CRMIntegration:
    def create_lead(self, customer_data):
        # Integrate with Salesforce, HubSpot, etc.
        pass
    
    def update_customer(self, customer_id, updates):
        # Update customer information
        pass
```

#### Database Integration
```python
class DatabaseConnector:
    def __init__(self, connection_string):
        self.connection = self.connect(connection_string)
    
    def save_conversation(self, conversation_data):
        # Save to your database
        pass
```

---

## 12. Monitoring & Analytics

### 12.1 LangFuse Integration

#### Setting Up Monitoring
```python
# In your agent files
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="your-public-key",
    secret_key="your-secret-key"
)

# Track conversations
trace = langfuse.trace(
    name="customer_conversation",
    metadata={"conversation_id": conversation_id}
)
```

#### Key Metrics to Monitor
1. **Conversation Success Rate**: Percentage of completed interactions
2. **Response Time**: Average time to generate responses
3. **Intent Classification Accuracy**: Accuracy of intent detection
4. **User Satisfaction**: Based on conversation outcomes
5. **API Usage**: Token consumption and costs

### 12.2 Custom Analytics

#### Implementing Custom Metrics
```python
class AnalyticsCollector:
    def track_conversation_start(self, conversation_id):
        # Track conversation initiation
        pass
    
    def track_intent_classification(self, intent, confidence):
        # Track intent detection accuracy
        pass
    
    def track_conversation_completion(self, conversation_id, success):
        # Track successful completions
        pass
```

#### Dashboard Integration
```python
# Integration with analytics platforms
class DashboardIntegration:
    def send_metrics_to_datadog(self, metrics):
        # Send to Datadog
        pass
    
    def send_metrics_to_grafana(self, metrics):
        # Send to Grafana
        pass
```

### 12.3 Performance Monitoring

#### Health Check Endpoints
```python
@app.route('/health')
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "dependencies": {
            "openai": check_openai_status(),
            "langfuse": check_langfuse_status()
        }
    }
```

#### Alerting Setup
```python
class AlertManager:
    def setup_alerts(self):
        # Configure alerts for:
        # - High error rates
        # - Slow response times
        # - API failures
        # - Resource usage thresholds
        pass
```

---

## Appendix A: Configuration Files

### A.1 Docker Configuration
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "run.py"]
```

### A.2 Docker Compose
```yaml
version: '3.8'
services:
  medagent:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
    volumes:
      - ./logs:/app/logs
  
  mongodb:
    image: mongo:latest
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db

volumes:
  mongodb_data:
```

---

## Appendix B: API Reference

### B.1 Complete API Specification
```yaml
openapi: 3.0.0
info:
  title: MedAgent API
  version: 1.0.0
  description: AI Call Center Automation API

paths:
  /process_voice:
    post:
      summary: Process voice input
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                audio:
                  type: string
                  format: binary
                conversation_id:
                  type: string
      responses:
        200:
          description: Successful response
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                  response:
                    type: string
                  intent:
                    type: string
                  audio_url:
                    type: string
```

---

## Appendix C: Troubleshooting Checklist

### C.1 Pre-Deployment Checklist
- [ ] All environment variables configured
- [ ] API keys validated and working
- [ ] Dependencies installed correctly
- [ ] Database connection established
- [ ] Microphone permissions granted
- [ ] Browser compatibility verified
- [ ] HTTPS certificate configured (production)
- [ ] Monitoring and logging enabled

### C.2 Common Error Codes
- **ERR_001**: OpenAI API key invalid or expired
- **ERR_002**: LangFuse connection failed
- **ERR_003**: Microphone access denied
- **ERR_004**: Audio processing failed
- **ERR_005**: Agent routing error
- **ERR_006**: Database connection lost
- **ERR_007**: Rate limit exceeded
- **ERR_008**: Invalid conversation state

---

**Document Version**: 1.0  
**Last Updated**: June 25, 2025  
**Next Review**: July 25, 2025

For technical support or questions, please contact the development team or refer to the project repository documentation.

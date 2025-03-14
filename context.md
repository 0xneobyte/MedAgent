# AI-Powered Multi-Agentic Healthcare System

## **Project Overview**

This project aims to develop an **AI-powered multi-agent system** for **automated patient voice interaction, appointment scheduling, and notifications** in healthcare settings. The system integrates **LangGraph** for structured multi-agent workflows, **LangFuse** for telemetry and monitoring, **OpenAI Whisper** for speech-to-text transcription, and **GPT-4o** for natural language understanding and response generation. Additionally, **Web Speech API** is used for microphone input and Text-to-Speech (TTS) output, while **SendGrid** handles email communications. This creates a dynamic conversational AI system that can **speak back to users** and continue the conversation fluidly through a web interface.

## **Key Technologies Used**

### **1️⃣ LangGraph (Agent Workflow & Orchestration)**

- LangGraph is a **graph-based framework** that enables complex graph-based reasoning chains.
- It provides a robust way to **route different patient queries** to the appropriate AI agent.
- **StateGraph** architecture allows for tracking stateful interactions across the conversation.
- Ensures efficient multi-agent collaboration for **seamless automation** in healthcare.

### **2️⃣ LangFuse (AI Telemetry & Logging)**

- LangFuse is used to **track AI interactions** and **log conversation flows**.
- Helps in **debugging errors, improving response quality**, and monitoring how AI agents handle patient requests.
- Useful for **real-time performance monitoring** and debugging in production systems.

### **3️⃣ Whisper (Speech-to-Text Transcription)**

- OpenAI's **Whisper model** transcribes **user voice input into text**, allowing AI models to process the spoken conversation.
- Ensures **accurate and real-time voice recognition** for patient interactions.

### **4️⃣ OpenAI Models (Natural Language Processing)**

- **GPT-4o** handles all language processing tasks across the system.
- Different configurations of the model handle different types of tasks:
  - Complex reasoning and sentiment analysis
  - Routine classification and information retrieval
  - Natural language generation for responses
- This unified approach ensures consistency while maintaining high performance.

### **5️⃣ Communications Integration (Web Speech API & SendGrid)**

- **Web Speech API** is used to **capture microphone input** and provide text-to-speech output in the web application.
- It allows the AI agent to **speak back** to the user in a natural voice directly in the browser.
- **SendGrid** provides templated email communications with tracking capabilities.

### **6️⃣ Database Integration (MongoDB & Mongoose)**

- **MongoDB with Mongoose** serves as the system of record for patient appointments and medical information.
- Stores appointment schedules, patient contact information, communication preferences, and interaction history.
- Enables real-time synchronization with proper error handling and conflict resolution protocols.

## **Multi-Agent System Architecture**

### 🚀 **How the System Works Step-by-Step**

### **Step 1: User Initiates Conversation**

- A **patient visits the web application** and clicks on the microphone button to start interacting.
- The web app **activates the microphone** and prepares to capture user voice input.

### **Step 2: AI Greets the User**

- The **web application plays a greeting**:
  _"Hello, this is the AI Assistant. How can I help you today?"_
- The system then **records the patient's voice** through the microphone.

### **Step 3: Speech-to-Text Conversion (Whisper)**

- The **recorded audio** is sent to the server.
- **OpenAI Whisper** transcribes the patient's speech into text.

### **Step 4: AI Understands the Query (GPT-4o)**

- The transcribed text is processed to identify the patient's intent and the level of the question.
- Based on the classification, the request is **routed to the appropriate specialized agent**.

### **Step 5: AI Speaks Back (Text-to-Speech via Web Speech API)**

- The AI-generated response is **converted into speech** using **Web Speech API**.
- The browser **plays back the AI's response** to the patient.

### **Step 6: Conversation Continues (Looping AI Responses)**

- The system **records the patient's next response** through the microphone.
- The cycle **repeats**, enabling a **fluid and dynamic conversation**.
- The conversation continues **until the user ends the interaction**.

## **Key AI Agents & Their Roles**

### 🤖 **AI Receptionist Agent**

- First point of contact for **handling voice interactions**.
- Uses **Whisper** for transcribing and AI models for understanding the patient's query.
- Processes user intent, identifies the level of the question, and routes requests accordingly.
- Directs them to the appropriate specialized agent.

### 📅 **Appointment Management Agent**

- Manages **scheduling, rescheduling, and cancellations**.
- Interfaces directly with the clinic's calendar system.
- Understands complex scheduling constraints including provider availability, appointment types, and duration requirements.
- Handles conflict resolution and optimization of the appointment calendar.

### 📢 **Notification & Messaging Agent**

- Manages the timing and content of all **outbound communications**.
- Personalizes messages based on patient preferences, appointment types, and historical interaction patterns.
- Sends automated **email notifications (via SendGrid)**.
- Handles delivery confirmations and escalates failed delivery attempts.

### 📞 **Call Center Agent**

- Maintains a comprehensive knowledge base of frequently asked questions, clinic policies, and service offerings.
- Handles multi-turn conversations and requests clarification when needed.
- Appropriately escalates complex or sensitive inquiries.
- Responds to common patient queries about clinic hours, services, directions, and preparations.

### 🛡 **Content Management Agent**

- Checks the LLM response against historical interactions.
- Validates that information provided is current, compliant with medical guidelines and privacy regulations.
- Ensures consistency with previous communications to the same patient.
- Serves as a quality control mechanism.

## **Memory Framework**

- Uses a short-term memory system to maintain conversation context during patient interactions:
  - **Conversation Memory**: Stores recent conversation turns (last 3-5 exchanges)
  - **Patient History Cache**: Temporarily stores active patient details during the interaction

## **LangGraph Workflow Implementation**

- LangGraph is used to **define AI workflows**, ensuring smooth coordination between agents.

```python
from langgraph.graph import StateGraph
class PatientState:
    def __init__(self):
        self.intent = None
        self.details = None
workflow = StateGraph(PatientState)
def receptionist(state):
    state.intent = process_query(state.details)
    return state
workflow.add_node("Receptionist", receptionist)
workflow.set_entry_point("Receptionist")
```

## **LangFuse for Logging & AI Monitoring**

- LangFuse **logs and monitors AI agent interactions**.
- Helps **debug errors, track patient interactions**, and **optimize AI decision-making**.

```python
from langfuse import LangFuse
langfuse = LangFuse(public_key="your_public_key", secret_key="your_secret_key")
langfuse.log_event("AI Response", {"query": "Book an appointment", "response": response})
```

## **Next Steps & Deployment Plan**

✅ **Fine-tune AI conversational flow** for real-world use.  
✅ **Develop responsive web application** with microphone integration.  
✅ **Deploy Flask API** using **AWS/GCP for live demo**.  
✅ **Enhance AI decision-making** using **LangGraph workflows**.  
✅ **Improve AI accuracy** with **LangFuse telemetry tracking**.

---

This `context.md` provides **Cursor AI** with an in-depth understanding of the project. Let me know if you need further refinements! 🚀

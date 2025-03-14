import os
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

# Simple knowledge base for demo purposes
KNOWLEDGE_BASE = {
    "hours": {
        "question": ["what are your hours", "when are you open", "office hours"],
        "answer": "Our clinic is open Monday through Friday from 9:00 AM to 5:00 PM, and on Saturdays from 9:00 AM to 1:00 PM. We are closed on Sundays and major holidays."
    },
    "services": {
        "question": ["what services do you offer", "what do you treat", "what medical services", "what can you help with"],
        "answer": "Our clinic offers primary care services, including annual check-ups, vaccinations, illness treatment, and management of chronic conditions. We also provide specialist referrals and basic laboratory services."
    },
    "location": {
        "question": ["where are you located", "what's your address", "how do i get to your clinic", "directions"],
        "answer": "Our clinic is located at 123 Medical Drive, Suite 100, in downtown. We are easily accessible by public transportation and have free parking available for patients."
    },
    "insurance": {
        "question": ["do you accept insurance", "what insurance plans", "is my insurance covered", "payment options"],
        "answer": "We accept most major insurance plans, including Medicare and Medicaid. Please bring your insurance card to your appointment so we can verify your coverage. We also offer affordable self-pay options for those without insurance."
    },
    "covid": {
        "question": ["covid protocols", "covid testing", "covid vaccine", "mask requirements", "coronavirus"],
        "answer": "We offer COVID-19 testing and vaccinations. We follow CDC guidelines for safety protocols. Masks are currently optional but recommended for those who are immunocompromised or experiencing respiratory symptoms."
    },
    "doctors": {
        "question": ["who are your doctors", "medical staff", "specialists", "practitioners"],
        "answer": "Our clinic has a team of board-certified physicians specializing in family medicine, internal medicine, and pediatrics. We also have nurse practitioners and physician assistants who work alongside our doctors to provide comprehensive care."
    }
}

def call_center_agent(state):
    """
    The main Call Center Agent function for LangGraph
    
    Args:
        state: The current state object from LangGraph
    
    Returns:
        dict: Updated state with response to general inquiries
    """
    # Only process if the intent is a general inquiry
    if state.get("intent") != "general_inquiry":
        return state
    
    # Create a trace in Langfuse
    trace = langfuse.trace(
        name="call_center_agent",
        metadata={
            "transcript": state.get("transcript", ""),
            "intent": "general_inquiry"
        }
    )
    
    try:
        # Extract the transcript from the state
        transcript = state.get("transcript", "")
        
        # Check if the query matches any knowledge base items
        knowledge_base_match = None
        matched_category = None
        matched_phrase = None
        
        for category, data in KNOWLEDGE_BASE.items():
            for phrase in data["question"]:
                if phrase.lower() in transcript.lower():
                    knowledge_base_match = data["answer"]
                    matched_category = category
                    matched_phrase = phrase
                    break
            if knowledge_base_match:
                break
        
        # If we found a match, create a span with the match information
        if knowledge_base_match:
            trace.span(
                name="knowledge_base_match",
                metadata={
                    "matched_category": matched_category,
                    "matched_phrase": matched_phrase
                }
            )
            state["response"] = knowledge_base_match
        else:
            # Create a Langfuse span for GPT response without using context manager
            span = trace.span(name="gpt4_general_inquiry")
            
            # If no direct match, use GPT-4o for a response
            system_prompt = """
            You are an AI assistant for a healthcare clinic. Your goal is to provide helpful, accurate, 
            and concise responses to patient inquiries about clinic services, policies, and general 
            medical information. 
            
            Here are some guidelines:
            1. Provide accurate information about clinic services, hours, and policies.
            2. For general medical information, provide widely accepted information but avoid making specific diagnoses.
            3. If asked about emergencies, always advise patients to call 911 or go to the nearest emergency room.
            4. Keep responses friendly, professional, and concise.
            5. Do not provide information on prescription drugs or treatment recommendations.
            6. If you're unsure about something, acknowledge that and suggest the patient speak with a healthcare provider.
            
            Remember, you represent a healthcare clinic, so maintain professionalism at all times.
            """
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript}
                ],
                temperature=0.7
            )
            
            state["response"] = response.choices[0].message.content
            
            # Create a new span with the response length metadata
            trace.span(
                name="response_metadata", 
                metadata={"response_length": len(state["response"])}
            )
            
            # End the original span
            span.end()
        
        trace.update(status="success")
    
    except Exception as e:
        trace.update(status="error", error={"message": str(e)})
        print(f"Error in call center agent: {e}")
        state["response"] = "I'm having trouble finding information about that. Please try asking in a different way or contact our office directly for more information."
    
    return state 
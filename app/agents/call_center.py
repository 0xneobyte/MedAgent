import os
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
    },
    "greeting": {
        "question": ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "howdy", "greetings"],
        "answer": "Hello! I'm your healthcare AI assistant. How can I help you today with your healthcare needs?"
    },
    "thanks": {
        "question": ["thank you", "thanks", "appreciate it", "thank you so much", "thx"],
        "answer": "You're welcome! I'm happy to help with any other questions you might have about our clinic or your health concerns."
    },
    "goodbye": {
        "question": ["goodbye", "bye", "see you", "talk to you later", "good night"],
        "answer": "Goodbye! Please don't hesitate to reach out if you have any other questions. Have a great day!"
    },
    "name": {
        "question": ["what's your name", "who are you", "what should I call you", "your name", "can I know your name"],
        "answer": "I'm MedAgent, your AI healthcare assistant. I'm here to help you with scheduling appointments, answering questions about our services, and providing general health information."
    },
    "patient_name": {
        "question": ["my name", "what's my name", "do you know my name", "can I know my name"],
        "answer": "I can see information you've shared during our conversation, including your name if you've provided it earlier. How else can I assist you today?"
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
    intent = state.get('intent', 'unknown')
    conversation_id = state.get("conversation_id", "unknown")
    
    logger.info(f"Call Center Agent: Handling '{intent}' inquiry [ID: {conversation_id}]")
    
    # Extract the transcript from the state
    transcript = state.get("transcript", "")
    
    try:
        # First, prioritize health-related queries over simple keyword matching
        # Check if it's a health-related query (including specialist recommendations)
        is_health_query = False
        health_terms = ["pain", "hurt", "sick", "fever", "headache", "cough", "symptom", 
                      "heart", "blood", "doctor", "medicine", "prescription", "allergy", 
                      "condition", "medical", "health", "treatment", "cancer", "disease", 
                      "infection", "diagnosis", "surgery", "emergency", "specialist", 
                      "test", "lab", "results"]
        
        for term in health_terms:
            if term in transcript.lower():
                is_health_query = True
                break
                
        # Additional check for doctor recommendation queries
        doctor_recommendation_patterns = [
            "which doctor", "recommend a doctor", "suggest a doctor", "which specialist",
            "need a doctor for", "doctor would you suggest", "doctor should i see",
            "specialist for", "what kind of doctor"
        ]
        
        if not is_health_query:
            for pattern in doctor_recommendation_patterns:
                if pattern in transcript.lower():
                    is_health_query = True
                    break
        
        # If it's a health query, handle it with the health-specific GPT logic
        if is_health_query:
            logger.info("Processing health-related inquiry with specialized medical guidance")
            
            # Enhanced health-specific prompt for both general health questions and specialist recommendations
            system_prompt = """
            You are an AI assistant for a healthcare clinic. Your goal is to provide helpful information about 
            health concerns while being careful not to give definitive medical advice or diagnoses.
            
            Guidelines:
            1. Express empathy for health concerns
            2. Provide general, widely accepted information
            3. Always recommend speaking with a healthcare professional for specific concerns
            4. For serious symptoms (chest pain, difficulty breathing, etc.), advise seeking immediate medical attention
            5. Keep responses informative but conservative - focus on next steps rather than speculating about conditions
            6. Be friendly and reassuring while maintaining professionalism
            
            For doctor/specialist recommendation questions:
            1. Provide information about which type of specialist typically handles the mentioned condition
            2. For headaches: suggest general practitioners initially, then neurologists for persistent issues
            3. For heart issues: suggest cardiologists
            4. For skin conditions: suggest dermatologists
            5. For joint/muscle pain: suggest orthopedic specialists or rheumatologists
            6. For digestive issues: suggest gastroenterologists
            7. Recommend that patients should first see their primary care doctor who can provide appropriate referrals
            
            Remember, you cannot diagnose conditions or prescribe treatments, but you can provide general guidance 
            about which types of medical specialists handle different health concerns.
            """
            
            # Send the transcript to GPT-4o with our enhanced health prompt
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ]
            
            # Create a Langfuse generation for proper cost tracking
            generation = langfuse.start_generation(
                name="health_inquiry_gpt4",
                model="gpt-4o",
                input=messages,
                metadata={"temperature": 0.5, "query_type": "health_related"}
            )
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.5
            )
            
            state["response"] = response.choices[0].message.content
            
            # Update generation with output and usage data for cost tracking
            generation.update(
                output=state["response"],
                usage_details={
                    "input": response.usage.prompt_tokens,
                    "output": response.usage.completion_tokens,
                    "total": response.usage.total_tokens
                }
            )
            generation.end()
            
            logger.info(f"Health inquiry response generated (tokens: {response.usage.total_tokens})")
            
        else:
            # Continue with the regular flow for non-health queries
            # Check if the query matches any knowledge base items
            knowledge_base_match = None
            matched_category = None
            
            for category, data in KNOWLEDGE_BASE.items():
                for phrase in data["question"]:
                    if phrase.lower() in transcript.lower():
                        knowledge_base_match = data["answer"]
                        matched_category = category
                        break
                if knowledge_base_match:
                    break
            
            # If we found a match, respond with the knowledge base answer
            if knowledge_base_match:
                state["response"] = knowledge_base_match
                logger.info(f"Response generated from knowledge base: '{matched_category}' category")
            else:
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
                7. For simple greetings or brief remarks, respond naturally and warmly.
                8. If asked about personal information, respond in a friendly way while respecting privacy boundaries.
                
                Remember, you represent a healthcare clinic, so maintain professionalism at all times.
                """
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript}
                ]
                
                # Create a Langfuse generation for proper cost tracking
                generation = langfuse.start_generation(
                    name="general_inquiry_gpt4",
                    model="gpt-4o",
                    input=messages,
                    metadata={"temperature": 0.7, "query_type": "general_inquiry"}
                )
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.7
                )
                
                state["response"] = response.choices[0].message.content
                
                # Update generation with output and usage data for cost tracking
                generation.update(
                    output=state["response"],
                    usage_details={
                        "input": response.usage.prompt_tokens,
                        "output": response.usage.completion_tokens,
                        "total": response.usage.total_tokens
                    }
                )
                generation.end()
                
                logger.info(f"General inquiry response generated via GPT-4o (tokens: {response.usage.total_tokens})")
        
        logger.info(f"Call Center Agent: Response processing complete")
    
    except Exception as e:
        logger.error(f"Error in call center agent: {e}")
        state["response"] = "I'm having trouble finding information about that. Please try asking in a different way or contact our office directly for more information."
    
    return state 
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

# Define healthcare compliance guidelines
COMPLIANCE_GUIDELINES = [
    "No specific treatment recommendations should be made.",
    "No diagnoses should be provided.",
    "No prescription drug information should be given.",
    "Emergency situations should direct patients to call 911 or go to the ER.",
    "Patient privacy should be maintained at all times.",
    "Responses should be professionally worded.",
    "Medical information should be factually accurate.",
    "Responses should not promise medical outcomes."
]

def content_management_agent(state):
    """
    The main Content Management Agent function for LangGraph
    
    Args:
        state: The current state object from LangGraph
    
    Returns:
        dict: Updated state with validated response
    """
    # If there's no response, nothing to validate
    if "response" not in state:
        state["response"] = "I'm sorry, but I don't have enough information to provide a response."
        return state
    
    # Create a trace in Langfuse
    trace = langfuse.trace(
        name="content_management",
        metadata={
            "original_response": state["response"],
            "intent": state.get("intent", "unknown")
        }
    )
    
    try:
        # Extract the response from the state
        response = state["response"]
        
        # For demo purposes, perform a simple validation check
        # In a real system, this would be more sophisticated
        problematic_phrases = [
            "I diagnose you with",
            "you should take",
            "I recommend this medication",
            "this drug will help",
            "I can prescribe",
            "you definitely have"
        ]
        
        # Check if any problematic phrases are in the response
        issues_found = []
        for phrase in problematic_phrases:
            if phrase.lower() in response.lower():
                issues_found.append(phrase)
        
        # If issues were found, modify the response
        if issues_found:
            trace.add_metadata({"issues_found": issues_found})
            
            with trace.span(name="gpt4_content_correction") as span:
                # Use GPT-4o to fix the response
                system_prompt = f"""
                You are an AI content reviewer for a healthcare clinic. Review the following response 
                for compliance issues and modify it to be compliant with these guidelines:
                
                Guidelines:
                {', '.join(COMPLIANCE_GUIDELINES)}
                
                The following problematic phrases were identified:
                {', '.join(issues_found)}
                
                Rewrite the response to fix these issues while maintaining the helpful intent and core information.
                """
                
                correction_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": response}
                    ],
                    temperature=0.3
                )
                
                # Update the response
                state["response"] = correction_response.choices[0].message.content
                span.add_metadata({
                    "original_response": response,
                    "modified_response": state["response"]
                })
        else:
            # No issues found, but still track it in Langfuse
            trace.add_metadata({"validated": True, "changes_needed": False})
        
        # In a more advanced system, we could also:
        # 1. Check response against a vector store of previous responses
        # 2. Validate medical claims against a medical knowledge base
        # 3. Ensure consistency with previous communications
        
        trace.update(status="success")
    
    except Exception as e:
        trace.update(status="error", error={"message": str(e)})
        print(f"Error in content management agent: {e}")
        # We won't change the response on error - just log the issue
    
    return state 
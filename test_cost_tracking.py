#!/usr/bin/env python3
"""
Test script to verify that Langfuse cost tracking is properly implemented
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test imports
try:
    from langfuse import Langfuse
    print("✅ Langfuse import successful")
except Exception as e:
    print(f"❌ Langfuse import failed: {e}")
    exit(1)

try:
    from openai import OpenAI
    print("✅ OpenAI import successful")
except Exception as e:
    print(f"❌ OpenAI import failed: {e}")
    exit(1)

# Initialize clients
try:
    langfuse = Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    )
    print("✅ Langfuse client initialized")
except Exception as e:
    print(f"❌ Langfuse client initialization failed: {e}")
    exit(1)

try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    print("✅ OpenAI client initialized")
except Exception as e:
    print(f"❌ OpenAI client initialization failed: {e}")
    exit(1)

# Test a simple generation with cost tracking
def test_cost_tracking():
    print("\n🧪 Testing cost tracking with a simple generation...")
    
    # Test messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Respond with exactly one word."},
        {"role": "user", "content": "Say hello"}
    ]
    
    # Create a generation for proper cost tracking
    generation = langfuse.start_generation(
        name="test_generation",
        model="gpt-4o",
        input=messages,
        metadata={"temperature": 0.1, "max_tokens": 5}
    )
    
    try:
        # Make API call
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.1,
            max_tokens=5
        )
        
        output = response.choices[0].message.content.strip()
        
        # Update generation with output and usage data for cost tracking
        generation.update(
            output=output,
            usage_details={
                "input": response.usage.prompt_tokens,
                "output": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
        )
        
        # End the generation
        generation.end()
        
        print(f"✅ Cost tracking test successful!")
        print(f"   Response: {output}")
        print(f"   Tokens used: {response.usage.total_tokens}")
        print(f"   Input tokens: {response.usage.prompt_tokens}")
        print(f"   Output tokens: {response.usage.completion_tokens}")
        print("\n🎉 Generation with usage tracking has been sent to Langfuse!")
        print("   Check your Langfuse dashboard - you should now see model costs!")
        
    except Exception as e:
        generation.end()
        print(f"❌ Cost tracking test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔍 Testing Langfuse cost tracking implementation...")
    success = test_cost_tracking()
    
    if success:
        print("\n✅ All tests passed! Cost tracking should now be working in Langfuse.")
        print("💡 The key changes made:")
        print("   - Replaced spans with generations for OpenAI API calls")
        print("   - Added usage data (input/output/total tokens) to generations")
        print("   - Updated all agent files with proper cost tracking")
    else:
        print("\n❌ Tests failed. Please check the error messages above.")

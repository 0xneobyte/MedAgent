import os
from dotenv import load_dotenv

# Load environment variables before importing any modules that use them
load_dotenv()

# Import models first to ensure DB connection is initialized
from app.models import Doctor

# Import the app after environment variables are loaded
from app.app import app

if __name__ == "__main__":
    # Initialize sample data in MongoDB
    try:
        Doctor.seed_sample_doctors()
        print("MongoDB initialized with sample doctors data")
    except Exception as e:
        print(f"Warning: Failed to initialize MongoDB with sample data: {e}")
        print("The application will still work but appointment booking functionality may be limited.")
        print("Please ensure MongoDB is running and MONGODB_URI is set in your .env file.")
    
    print("Starting MedAgent - AI Healthcare Assistant")
    print("Visit http://localhost:5001 to use the application")
    # Disable auto-reloader to prevent in-memory conversation_store from being reset
    app.run(debug=True, host="0.0.0.0", port=5001, use_reloader=False) 
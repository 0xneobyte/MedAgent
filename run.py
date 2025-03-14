import os
from dotenv import load_dotenv

# Load environment variables before importing any modules that use them
load_dotenv()

from app.app import app

if __name__ == "__main__":
    print("Starting MedAgent - AI Healthcare Assistant")
    print("Visit http://localhost:5001 to use the application")
    app.run(debug=True, host="0.0.0.0", port=5001) 
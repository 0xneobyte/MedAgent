from app.app import app

if __name__ == "__main__":
    print("Starting MedAgent - AI Healthcare Assistant")
    print("Visit http://localhost:5000 to use the application")
    app.run(debug=True, host="0.0.0.0") 
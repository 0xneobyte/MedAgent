from pymongo import MongoClient
from datetime import datetime
import os
from dateutil.relativedelta import relativedelta

# Connect to MongoDB
client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
db = client["medagent_db"]

# Collections
patients_collection = db["patients"]
doctors_collection = db["doctors"]
appointments_collection = db["appointments"]

def calculate_age(birthdate):
    """Calculate age from birthdate"""
    if isinstance(birthdate, str):
        birthdate = datetime.strptime(birthdate, "%Y-%m-%d")
    
    today = datetime.now()
    age = relativedelta(today, birthdate).years
    return age

class Patient:
    @staticmethod
    def create(name, phone, email, birthdate):
        """Create a new patient record"""
        age = calculate_age(birthdate)
        
        patient_data = {
            "name": name,
            "phone": phone,
            "email": email,
            "birthdate": birthdate,
            "age": age,
            "created_at": datetime.now()
        }
        
        # Check if patient already exists with this phone or email
        existing_patient = patients_collection.find_one({
            "$or": [
                {"phone": phone},
                {"email": email}
            ]
        })
        
        if existing_patient:
            # Update existing patient info
            patients_collection.update_one(
                {"_id": existing_patient["_id"]},
                {"$set": {
                    "name": name,
                    "email": email,
                    "birthdate": birthdate,
                    "age": age,
                    "updated_at": datetime.now()
                }}
            )
            return existing_patient["_id"]
        else:
            # Insert new patient
            result = patients_collection.insert_one(patient_data)
            return result.inserted_id
    
    @staticmethod
    def find_by_phone(phone):
        """Find a patient by phone number"""
        return patients_collection.find_one({"phone": phone})
    
    @staticmethod
    def find_by_email(email):
        """Find a patient by email"""
        return patients_collection.find_one({"email": email})

class Doctor:
    @staticmethod
    def find_by_specialty(specialty):
        """Find doctors by specialty"""
        return list(doctors_collection.find({"specialty": specialty}))
    
    @staticmethod
    def get_available_slots(doctor_id, date):
        """Get available time slots for a doctor on a specific date"""
        doctor = doctors_collection.find_one({"_id": doctor_id})
        if not doctor:
            return []
        
        # Get all available time slots from doctor's schedule
        all_slots = doctor.get("available_slots", {}).get(date, [])
        
        # Find booked slots on that date for this doctor
        booked_appointments = appointments_collection.find({
            "doctor_id": doctor_id,
            "date": date
        })
        
        booked_slots = [appt["time"] for appt in booked_appointments]
        
        # Return only the available slots
        return [slot for slot in all_slots if slot not in booked_slots]
    
    @staticmethod
    def get_specialty_for_reason(reason):
        """Recommend a doctor specialty based on the reason for visit"""
        # This is a simplified mapping - in a real system this would be more sophisticated
        reason_to_specialty = {
            "headache": "Neurologist",
            "migraine": "Neurologist",
            "chest pain": "Cardiologist",
            "heart": "Cardiologist",
            "rash": "Dermatologist",
            "skin": "Dermatologist",
            "stomach": "Gastroenterologist",
            "digestion": "Gastroenterologist",
            "joint pain": "Orthopedic",
            "bone": "Orthopedic",
            "fracture": "Orthopedic",
            "breathing": "Pulmonologist",
            "cough": "Pulmonologist",
            "vision": "Ophthalmologist",
            "eye": "Ophthalmologist",
            "ear": "ENT Specialist",
            "throat": "ENT Specialist",
            "nose": "ENT Specialist",
            "mental health": "Psychiatrist",
            "depression": "Psychiatrist",
            "anxiety": "Psychiatrist",
            "women's health": "Gynecologist",
            "pregnancy": "Gynecologist",
            "child": "Pediatrician",
            "allergy": "Allergist",
            "diabetes": "Endocrinologist",
            "hormone": "Endocrinologist",
            "kidney": "Nephrologist",
            "urinary": "Urologist",
            "cancer": "Oncologist"
        }
        
        # Default to general practitioner if no specific match
        reason_lower = reason.lower()
        
        for keyword, specialty in reason_to_specialty.items():
            if keyword in reason_lower:
                return specialty
        
        return "General Practitioner"
    
    @staticmethod
    def seed_sample_doctors():
        """Add sample doctors to the database if empty"""
        if doctors_collection.count_documents({}) == 0:
            doctors = [
                {
                    "name": "Dr. Smith",
                    "specialty": "General Practitioner",
                    "available_slots": {
                        # Format: YYYY-MM-DD: [time slots]
                        datetime.now().strftime("%Y-%m-%d"): ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"],
                        (datetime.now() + relativedelta(days=1)).strftime("%Y-%m-%d"): ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"],
                        (datetime.now() + relativedelta(days=2)).strftime("%Y-%m-%d"): ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
                    }
                },
                {
                    "name": "Dr. Johnson",
                    "specialty": "Cardiologist",
                    "available_slots": {
                        datetime.now().strftime("%Y-%m-%d"): ["09:30", "10:30", "13:30", "15:30"],
                        (datetime.now() + relativedelta(days=1)).strftime("%Y-%m-%d"): ["09:30", "10:30", "13:30", "15:30"],
                        (datetime.now() + relativedelta(days=2)).strftime("%Y-%m-%d"): ["09:30", "10:30", "13:30", "15:30"]
                    }
                },
                {
                    "name": "Dr. Williams",
                    "specialty": "Dermatologist",
                    "available_slots": {
                        datetime.now().strftime("%Y-%m-%d"): ["10:00", "11:00", "14:00", "15:00"],
                        (datetime.now() + relativedelta(days=1)).strftime("%Y-%m-%d"): ["10:00", "11:00", "14:00", "15:00"],
                        (datetime.now() + relativedelta(days=2)).strftime("%Y-%m-%d"): ["10:00", "11:00", "14:00", "15:00"]
                    }
                },
                {
                    "name": "Dr. Brown",
                    "specialty": "Pediatrician",
                    "available_slots": {
                        datetime.now().strftime("%Y-%m-%d"): ["09:00", "10:00", "11:00", "15:00", "16:00"],
                        (datetime.now() + relativedelta(days=1)).strftime("%Y-%m-%d"): ["09:00", "10:00", "11:00", "15:00", "16:00"],
                        (datetime.now() + relativedelta(days=2)).strftime("%Y-%m-%d"): ["09:00", "10:00", "11:00", "15:00", "16:00"]
                    }
                }
            ]
            
            doctors_collection.insert_many(doctors)

class Appointment:
    @staticmethod
    def create(patient_id, doctor_id, date, time, reason):
        """Create a new appointment"""
        appointment_data = {
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "date": date,
            "time": time,
            "reason": reason,
            "created_at": datetime.now(),
            "status": "scheduled"
        }
        
        result = appointments_collection.insert_one(appointment_data)
        return result.inserted_id
    
    @staticmethod
    def find_by_patient(patient_id):
        """Find all appointments for a patient"""
        return list(appointments_collection.find({"patient_id": patient_id}).sort("date", 1))
    
    @staticmethod
    def cancel(appointment_id):
        """Cancel an appointment"""
        appointments_collection.update_one(
            {"_id": appointment_id},
            {"$set": {"status": "cancelled", "updated_at": datetime.now()}}
        )

# Initialize sample data when imported
Doctor.seed_sample_doctors() 
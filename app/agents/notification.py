import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from langfuse.client import Langfuse
import datetime

# Initialize Langfuse for logging
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)

# For demo purposes, we'll simulate email sending
def send_email(to_email, subject, content):
    """
    Send an email using SendGrid
    
    Args:
        to_email: The recipient's email address
        subject: The email subject
        content: The HTML content of the email
    
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    # For demo, log but don't actually send
    print(f"Would send email to {to_email} with subject: {subject}")
    print(f"Content: {content}")
    
    # In production, we would use SendGrid to send the email
    if os.getenv("SENDGRID_API_KEY"):
        try:
            message = Mail(
                from_email=os.getenv("FROM_EMAIL", "clinic@example.com"),
                to_emails=to_email,
                subject=subject,
                html_content=content
            )
            
            sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
            response = sg.send(message)
            
            return response.status_code == 202
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    # In demo mode, always return success
    return True

def create_appointment_confirmation_email(appointment):
    """
    Create an email message for appointment confirmation
    
    Args:
        appointment: Dictionary containing appointment details
    
    Returns:
        tuple: (subject, content) for the email
    """
    # Format the date for better display
    try:
        date_obj = datetime.datetime.strptime(appointment["date"], "%Y-%m-%d")
        formatted_date = date_obj.strftime("%A, %B %d, %Y")
    except:
        formatted_date = appointment["date"]
    
    subject = "Your Appointment Confirmation"
    
    content = f"""
    <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 5px;">
                <div style="background-color: #4b6cb7; color: white; padding: 10px; text-align: center; border-radius: 5px 5px 0 0;">
                    <h2>Appointment Confirmation</h2>
                </div>
                <div style="padding: 20px;">
                    <p>Dear Patient,</p>
                    <p>Your appointment has been scheduled for:</p>
                    <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #4b6cb7; margin: 15px 0;">
                        <p><strong>Date:</strong> {formatted_date}</p>
                        <p><strong>Time:</strong> {appointment["time"]}</p>
                        <p><strong>Provider:</strong> {appointment["doctor"]}</p>
                        <p><strong>Reason:</strong> {appointment["reason"]}</p>
                    </div>
                    <p>Please arrive 15 minutes before your appointment time to complete any necessary paperwork.</p>
                    <p>If you need to reschedule or cancel, please call our office at (555) 123-4567 at least 24 hours before your appointment.</p>
                    <p>Thank you for choosing our clinic for your healthcare needs.</p>
                    <p>Best regards,<br>The Medical Office Team</p>
                </div>
                <div style="background-color: #f8f9fa; padding: 10px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 5px 5px;">
                    <p>123 Medical Drive, Suite 100 | City, State 12345 | (555) 123-4567</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    return subject, content

def notification_agent(state):
    """
    The main Notification Agent function for LangGraph
    
    Args:
        state: The current state object from LangGraph
    
    Returns:
        dict: Updated state with notification information
    """
    # Check if this is an appointment-related intent that requires notification
    if "schedule_appointment" not in state.get("intent", "") and "appointment" not in state.get("intent", ""):
        return state
    
    # Create a trace in Langfuse
    trace = langfuse.trace(
        name="notification_agent",
        metadata={
            "intent": state.get("intent", "unknown")
        }
    )
    
    try:
        # This is a simplified version for the demo
        # In a real system, we would extract the appointment details from the state
        # and send a proper notification to the patient
        
        # For demo purposes, we'll create a mock appointment
        appointment = {
            "id": "appt123",
            "patient_id": state.get("patient_id", "demo_patient"),
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "time": "14:00",
            "doctor": "Dr. Smith",
            "reason": "Consultation"
        }
        
        # Create the email content
        subject, content = create_appointment_confirmation_email(appointment)
        
        # In a real system, we would get the patient's email from the database
        # For demo, we'll use a placeholder
        patient_email = "patient@example.com"
        
        # Create a Langfuse span for timing
        with trace.span(name="send_email_notification") as span:
            # Send the email
            success = send_email(patient_email, subject, content)
            
            # Log the result
            span.add_metadata({
                "email_sent": success,
                "recipient": patient_email,
                "subject": subject
            })
        
        # Record the notification in the state
        state["notification_sent"] = success
        
        trace.update(status="success")
    
    except Exception as e:
        trace.update(status="error", error={"message": str(e)})
        print(f"Error in notification agent: {e}")
        state["notification_sent"] = False
    
    return state 
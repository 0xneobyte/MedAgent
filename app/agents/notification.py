import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from langfuse.client import Langfuse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Initialize Langfuse for logging
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)

def send_email(to_email, subject, html_content):
    """
    Send an email using SMTP or SendGrid
    
    Args:
        to_email: The recipient's email address
        subject: The email subject
        html_content: The HTML content of the email
    
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    # Log the email (for demo purposes)
    print(f"======= NOTIFICATION AGENT: SENDING EMAIL =======")
    print(f"TO: {to_email}")
    print(f"SUBJECT: {subject}")
    print(f"CONTENT: \n{html_content}\n")
    print(f"================================================")
    
    # Try to send using SMTP first
    if os.getenv("EMAIL_HOST") and os.getenv("EMAIL_USER") and os.getenv("EMAIL_PASSWORD"):
        try:
            print(f"Attempting to send email via SMTP...")
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = os.getenv("EMAIL_FROM", os.getenv("EMAIL_USER"))
            message["To"] = to_email
            
            # Attach HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Connect to SMTP server and send
            with smtplib.SMTP(os.getenv("EMAIL_HOST"), int(os.getenv("EMAIL_PORT", 587))) as server:
                server.starttls()  # Use TLS
                server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
                server.sendmail(
                    os.getenv("EMAIL_FROM", os.getenv("EMAIL_USER")),
                    to_email,
                    message.as_string()
                )
            print(f"Email sent successfully via SMTP to {to_email}")
            return True
        except Exception as e:
            print(f"Error sending email via SMTP: {e}")
            # Fall back to SendGrid if SMTP fails
    
    # If SMTP failed or is not configured, try SendGrid
    if os.getenv("SENDGRID_API_KEY"):
        try:
            print(f"Attempting to send email via SendGrid...")
            message = Mail(
                from_email=os.getenv("FROM_EMAIL", "noreply@medagent.example.com"),
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            
            sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
            response = sg.send(message)
            
            print(f"SendGrid response: {response.status_code}")
            return response.status_code == 202
        except Exception as e:
            print(f"Error sending email via SendGrid: {e}")
            return False
    else:
        # For demo purposes, just pretend it worked
        print("No email configuration found, pretending email was sent successfully (DEMO MODE)")
        return True

def create_appointment_confirmation_email(appointment_details):
    """
    Create the HTML content for an appointment confirmation email
    
    Args:
        appointment_details: A dictionary with appointment information
    
    Returns:
        str: The HTML content of the email
    """
    patient_name = appointment_details.get("patient_name", "Patient")
    formatted_date = appointment_details.get("formatted_date", "")
    time = appointment_details.get("time", "")
    doctor_name = appointment_details.get("doctor_name", "Doctor")
    doctor_specialty = appointment_details.get("doctor_specialty", "")
    reason = appointment_details.get("reason", "Consultation")
    appointment_id = appointment_details.get("appointment_id", "MA-00000")
    
    html_content = f"""
    <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 5px;">
                <div style="background-color: #4b6cb7; color: white; padding: 10px; text-align: center; border-radius: 5px 5px 0 0;">
                    <h2>Appointment Confirmation</h2>
                </div>
                <div style="padding: 20px;">
                    <p>Dear {patient_name},</p>
                    <p>Your appointment has been scheduled for:</p>
                    <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #4b6cb7; margin: 15px 0;">
                        <p><strong>Appointment ID:</strong> {appointment_id}</p>
                        <p><strong>Date:</strong> {formatted_date}</p>
                        <p><strong>Time:</strong> {time}</p>
                        <p><strong>Provider:</strong> {doctor_name} ({doctor_specialty})</p>
                        <p><strong>Reason:</strong> {reason}</p>
                    </div>
                    <p>Please save your appointment ID ({appointment_id}) for future reference. You will need this ID if you want to reschedule or cancel your appointment.</p>
                    <p>Please arrive 15 minutes before your appointment time to complete any necessary paperwork.</p>
                    <p>If you need to reschedule or cancel, please call our office at (555) 123-4567 at least 24 hours before your appointment and provide your appointment ID.</p>
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
    
    return html_content

def create_cancellation_confirmation_email(cancellation_details):
    """
    Create the HTML content for an appointment cancellation confirmation email
    
    Args:
        cancellation_details: A dictionary with cancelled appointment information
    
    Returns:
        str: The HTML content of the email
    """
    patient_name = cancellation_details.get("patient_name", "Patient")
    formatted_date = cancellation_details.get("formatted_date", "")
    time = cancellation_details.get("time", "")
    doctor_name = cancellation_details.get("doctor_name", "Doctor")
    appointment_id = cancellation_details.get("appointment_id", "MA-00000")
    
    html_content = f"""
    <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 5px;">
                <div style="background-color: #e74c3c; color: white; padding: 10px; text-align: center; border-radius: 5px 5px 0 0;">
                    <h2>Appointment Cancellation Confirmation</h2>
                </div>
                <div style="padding: 20px;">
                    <p>Dear {patient_name},</p>
                    <p>This email confirms that your appointment has been successfully cancelled:</p>
                    <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #e74c3c; margin: 15px 0;">
                        <p><strong>Appointment ID:</strong> {appointment_id}</p>
                        <p><strong>Date:</strong> {formatted_date}</p>
                        <p><strong>Time:</strong> {time}</p>
                        <p><strong>Provider:</strong> {doctor_name}</p>
                    </div>
                    <p>No further action is required on your part.</p>
                    <p>If you wish to schedule a new appointment, please contact our office at (555) 123-4567 or use our online scheduling system.</p>
                    <p>Thank you for letting us know about your cancellation.</p>
                    <p>Best regards,<br>The Medical Office Team</p>
                </div>
                <div style="background-color: #f8f9fa; padding: 10px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 5px 5px;">
                    <p>123 Medical Drive, Suite 100 | City, State 12345 | (555) 123-4567</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    return html_content

def notification_agent(state):
    """
    The main Notification Agent function for LangGraph
    
    Args:
        state: The current state object from LangGraph
    
    Returns:
        dict: Updated state with notification information
    """
    # Create a trace in Langfuse
    trace = langfuse.trace(
        name="notification_agent",
        metadata={
            "intent": state.get("intent", "unknown")
        }
    )
    
    try:
        # Get the intent and log it for debugging
        intent = state.get("intent", "")
        print(f"======= NOTIFICATION AGENT START =======")
        print(f"Notification agent received intent: {intent}")
        print(f"State keys: {list(state.keys())}")
        
        # Special check for cancellation handling
        has_cancellation_details = "cancellation_details" in state
        if has_cancellation_details:
            print(f"Found cancellation details in state: {state['cancellation_details']}")
            # Force intent to cancel_appointment if we have cancellation details 
            if intent != "cancel_appointment":
                print(f"Overriding intent from {intent} to cancel_appointment due to cancellation_details")
                intent = "cancel_appointment"
                state["intent"] = "cancel_appointment"
        
        # Check if this is a new appointment intent
        if intent in ["schedule_appointment", "book_appointment"] and "appointment_details" in state:
            print(f"Processing appointment booking notification...")
            # Get appointment details from state
            appointment_details = state["appointment_details"]
            print(f"Appointment details: {appointment_details}")
            
            # Create a span to track email sending
            email_span = trace.span(name="email_notification")
            
            # Get recipient email
            to_email = appointment_details.get("patient_email", "patient@example.com")
            
            # Create email subject and content
            subject = "Your Appointment Confirmation"
            html_content = create_appointment_confirmation_email(appointment_details)
            
            # Send the email
            email_sent = send_email(to_email, subject, html_content)
            
            # Log the result
            trace.span(
                name="email_result",
                metadata={
                    "email_sent": email_sent,
                    "recipient": to_email
                }
            )
            
            # End the email span
            email_span.end()
        
        # Check if this is a cancellation intent
        elif intent == "cancel_appointment" and has_cancellation_details:
            print(f"Processing cancellation notification...")
            # Get cancellation details from state
            cancellation_details = state["cancellation_details"]
            print(f"Cancellation details: {cancellation_details}")
            
            # Create a span to track email sending
            email_span = trace.span(name="cancellation_email_notification")
            
            # Get recipient email (might be None if cancelling without contact info collection)
            to_email = cancellation_details.get("patient_email")
            
            # If we don't have an email, try to get it from another source or use a default
            if not to_email:
                # Try to look up the patient's email if we have enough info
                # For now, just use a placeholder
                to_email = "patient@example.com"
                print(f"No email found in cancellation details, using default: {to_email}")
            else:
                print(f"Using email from cancellation details: {to_email}")
            
            # Create email subject and content
            subject = "Your Appointment Cancellation Confirmation"
            html_content = create_cancellation_confirmation_email(cancellation_details)
            
            # Send the email
            email_sent = send_email(to_email, subject, html_content)
            print(f"Cancellation email sent: {email_sent}")
            
            # Log the result
            trace.span(
                name="cancellation_email_result",
                metadata={
                    "email_sent": email_sent,
                    "recipient": to_email
                }
            )
            
            # End the email span
            email_span.end()
        else:
            print(f"No email notification needed for intent: {intent}")
        
        trace.update(status="success")
        print(f"======= NOTIFICATION AGENT END =======")
        
    except Exception as e:
        trace.update(status="error", error={"message": str(e)})
        print(f"Error in notification agent: {e}")
    
    # The notification agent doesn't modify the response
    return state 
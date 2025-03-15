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
    print(f"Would send email to {to_email} with subject: {subject}")
    print(f"Content: \n{html_content}\n")
    
    # Try to send using SMTP first
    if os.getenv("EMAIL_HOST") and os.getenv("EMAIL_USER") and os.getenv("EMAIL_PASSWORD"):
        try:
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
            message = Mail(
                from_email=os.getenv("FROM_EMAIL", "noreply@medagent.example.com"),
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            
            sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
            response = sg.send(message)
            
            return response.status_code == 202
        except Exception as e:
            print(f"Error sending email via SendGrid: {e}")
            return False
    else:
        # For demo purposes, just pretend it worked
        print("No email configuration found, pretending email was sent successfully")
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
                        <p><strong>Date:</strong> {formatted_date}</p>
                        <p><strong>Time:</strong> {time}</p>
                        <p><strong>Provider:</strong> {doctor_name} ({doctor_specialty})</p>
                        <p><strong>Reason:</strong> {reason}</p>
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
        # Check if this is an appointment-related intent
        intent = state.get("intent", "")
        
        if "appointment" in intent and "appointment_details" in state:
            # Get appointment details from state
            appointment_details = state["appointment_details"]
            
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
        
        trace.update(status="success")
        
    except Exception as e:
        trace.update(status="error", error={"message": str(e)})
        print(f"Error in notification agent: {e}")
    
    # The notification agent doesn't modify the response
    return state 
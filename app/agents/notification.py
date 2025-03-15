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

def create_reschedule_confirmation_email(reschedule_details):
    """
    Create a HTML email for appointment rescheduling confirmation
    
    Args:
        reschedule_details: Dictionary containing details of the rescheduled appointment
    
    Returns:
        str: HTML content of the email
    """
    # Unpack details (with defaults for safety)
    appointment_id = reschedule_details.get("appointment_id", "Unknown")
    patient_name = reschedule_details.get("patient_name", "Patient")
    doctor_name = reschedule_details.get("doctor_name", "Doctor")
    old_date = reschedule_details.get("old_date", "Unknown")
    old_time = reschedule_details.get("old_time", "Unknown")
    new_date = reschedule_details.get("formatted_new_date", reschedule_details.get("new_date", "Unknown"))
    new_time = reschedule_details.get("new_time", "Unknown")
    
    # Generate cancellation email HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>Appointment Rescheduled</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #4a69bd;
                    color: white;
                    padding: 15px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    padding: 20px;
                    border: 1px solid #ddd;
                    border-top: none;
                    border-radius: 0 0 5px 5px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    font-size: 0.8em;
                    color: #666;
                }}
                .highlight {{
                    font-weight: bold;
                    color: #4a69bd;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Appointment Rescheduled</h2>
            </div>
            <div class="content">
                <p>Dear {patient_name},</p>
                
                <p>This email confirms that your appointment has been <span class="highlight">rescheduled</span>.</p>
                
                <p><strong>Previous Appointment:</strong><br>
                Date: {old_date}<br>
                Time: {old_time}<br>
                Doctor: {doctor_name}<br>
                Appointment ID: {appointment_id}</p>
                
                <p><strong>New Appointment:</strong><br>
                Date: {new_date}<br>
                Time: {new_time}<br>
                Doctor: {doctor_name}<br>
                Appointment ID: {appointment_id}</p>
                
                <p>If you need to make any changes to your appointment, please contact us at (555) 123-4567 or reply to this email.</p>
                
                <p>Thank you for choosing our medical services.</p>
                
                <p>Best regards,<br>
                Medical Office Staff</p>
            </div>
            <div class="footer">
                <p>This is an automated message, please do not reply directly.</p>
                <p>© 2023 Medical Office. All rights reserved.</p>
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
        
        # Check if we have cancellation details either directly or in the appointment context
        cancellation_details = None
        has_cancellation_details = False
        
        # Try to get cancellation details from direct state
        if "cancellation_details" in state:
            cancellation_details = state["cancellation_details"]
            has_cancellation_details = True
            print(f"Found cancellation details directly in state")
        
        # If not in direct state, check appointment_context
        elif "appointment_context" in state and "cancellation_details" in state["appointment_context"]:
            cancellation_details = state["appointment_context"]["cancellation_details"]
            has_cancellation_details = True
            print(f"Found cancellation details in appointment_context")
            
            # Also add to root state for consistency
            state["cancellation_details"] = cancellation_details
        
        # Check if we have rescheduling details
        reschedule_details = None
        has_reschedule_details = False
        
        # Try to get rescheduling details from direct state
        if "reschedule_details" in state:
            reschedule_details = state["reschedule_details"]
            has_reschedule_details = True
            print(f"Found rescheduling details directly in state")
        
        # If not in direct state, check appointment_context
        elif "appointment_context" in state and "reschedule_details" in state["appointment_context"]:
            reschedule_details = state["appointment_context"]["reschedule_details"]
            has_reschedule_details = True
            print(f"Found rescheduling details in appointment_context")
            
            # Also add to root state for consistency
            state["reschedule_details"] = reschedule_details
        
        # Log whether we found cancellation details
        if has_cancellation_details:
            print(f"Cancellation details: {cancellation_details}")
            # Force intent to cancel_appointment if we have cancellation details 
            if intent != "cancel_appointment":
                print(f"Overriding intent from {intent} to cancel_appointment due to cancellation_details")
                intent = "cancel_appointment"
                state["intent"] = "cancel_appointment"
        
        # Log whether we found rescheduling details
        if has_reschedule_details:
            print(f"Rescheduling details: {reschedule_details}")
            # Force intent to reschedule_appointment if we have rescheduling details
            if intent != "reschedule_appointment":
                print(f"Overriding intent from {intent} to reschedule_appointment due to reschedule_details")
                intent = "reschedule_appointment"
                state["intent"] = "reschedule_appointment"
        
        # Check if this is a new appointment intent
        if intent in ["schedule_appointment", "book_appointment"] and "appointment_details" in state:
            appointment_details = state["appointment_details"]
            patient_email = appointment_details.get("patient_email")
            
            if patient_email:
                print(f"Sending appointment confirmation email to {patient_email}")
                # Create email content
                email_content = create_appointment_confirmation_email(appointment_details)
                
                # Send email
                send_email(
                    to_email=patient_email,
                    subject="Your Appointment Confirmation",
                    html_content=email_content
                )
                
                state["notification_sent"] = True
            else:
                print(f"No email address found for appointment confirmation")
                state["notification_sent"] = False
                
        # Handle cancellation email
        elif intent == "cancel_appointment" and has_cancellation_details:
            patient_email = cancellation_details.get("patient_email")
            
            if patient_email:
                print(f"Sending cancellation confirmation email to {patient_email}")
                # Create email content
                email_content = create_cancellation_confirmation_email(cancellation_details)
                
                # Send email
                send_email(
                    to_email=patient_email,
                    subject="Your Appointment Cancellation Confirmation",
                    html_content=email_content
                )
                
                state["notification_sent"] = True
            else:
                print(f"No email address found for cancellation confirmation")
                state["notification_sent"] = False
                
        # Handle rescheduling email
        elif intent == "reschedule_appointment" and has_reschedule_details:
            patient_email = reschedule_details.get("patient_email")
            
            if patient_email:
                print(f"Sending rescheduling confirmation email to {patient_email}")
                # Create email content
                email_content = create_reschedule_confirmation_email(reschedule_details)
                
                # Send email
                send_email(
                    to_email=patient_email,
                    subject="Your Appointment Reschedule Confirmation",
                    html_content=email_content
                )
                
                state["notification_sent"] = True
            else:
                print(f"No email address found for rescheduling confirmation")
                state["notification_sent"] = False
        else:
            # No notification needed or not enough info
            print(f"No notification sent - no matching intent or details")
            state["notification_sent"] = False
        
        print(f"======= NOTIFICATION AGENT END =======")
        trace.update(status="success")
    except Exception as e:
        print(f"Error in notification agent: {e}")
        trace.update(status="error", error={"message": str(e)})
        state["notification_sent"] = False
    
    return state 
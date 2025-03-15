# Setting Up Gmail SMTP for MedAgent

This guide explains how to configure your Gmail account to send emails from the MedAgent application.

## Create an App Password for Gmail

For security reasons, Gmail requires you to use an "App Password" instead of your regular account password:

1. Go to your Google Account: https://myaccount.google.com/
2. Select "Security" from the left menu
3. Under "Signing in to Google," select "2-Step Verification" (If not enabled, you'll need to enable it)
4. At the bottom of the page, select "App passwords"
5. Click "Select app" and choose "Other (Custom name)"
6. Enter "MedAgent" and click "Generate"
7. Google will display a 16-character password. **Copy this password**

## Configure Your .env File

Update your `.env` file with these settings:

```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your-gmail-address@gmail.com
EMAIL_PASSWORD=your-16-character-app-password
EMAIL_FROM=your-gmail-address@gmail.com
```

Make sure to replace:

- `your-gmail-address@gmail.com` with your actual Gmail address
- `your-16-character-app-password` with the app password you generated

## Test Your Configuration

1. Restart your MedAgent application
2. Go through the appointment booking process
3. Provide a real email address when prompted
4. After confirming your appointment, check the email inbox for the confirmation

## Troubleshooting

If you don't receive the email:

1. Check your server logs for SMTP-related errors
2. Verify that you've entered the correct app password
3. Make sure your Gmail account doesn't have additional security restrictions
4. Check your spam folder in case the email was filtered

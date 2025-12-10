# Email Setup for Render.com

This guide explains how to configure email sending for password reset functionality on Render.com.

## Option 1: Gmail SMTP (Recommended for Testing)

Gmail is the easiest option to set up and works well on Render.com.

### Steps:

1. **Enable App Password in Gmail:**
   - Go to your Google Account settings
   - Navigate to Security → 2-Step Verification (enable if not already)
   - Go to App Passwords
   - Generate a new app password for "Mail"
   - Copy the 16-character password

2. **Set Environment Variables in Render.com:**
   - Go to your Render.com dashboard
   - Select your service
   - Go to "Environment" tab
   - Add these environment variables:

   ```
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=true
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-16-char-app-password
   MAIL_DEFAULT_SENDER=your-email@gmail.com
   ```

3. **Redeploy your service** after adding the environment variables.

## Option 2: SendGrid (Recommended for Production)

SendGrid is a professional email service that works great on Render.com.

### Steps:

1. **Create SendGrid Account:**
   - Sign up at https://sendgrid.com (free tier available)
   - Verify your email address
   - Create an API Key in Settings → API Keys

2. **Set Environment Variables in Render.com:**
   ```
   MAIL_SERVER=smtp.sendgrid.net
   MAIL_PORT=587
   MAIL_USE_TLS=true
   MAIL_USERNAME=apikey
   MAIL_PASSWORD=your-sendgrid-api-key
   MAIL_DEFAULT_SENDER=your-verified-email@domain.com
   ```

## Option 3: Mailgun

Mailgun is another excellent option for transactional emails.

### Steps:

1. **Create Mailgun Account:**
   - Sign up at https://mailgun.com
   - Verify your domain or use sandbox domain for testing

2. **Set Environment Variables:**
   ```
   MAIL_SERVER=smtp.mailgun.org
   MAIL_PORT=587
   MAIL_USE_TLS=true
   MAIL_USERNAME=your-mailgun-username
   MAIL_PASSWORD=your-mailgun-password
   MAIL_DEFAULT_SENDER=noreply@your-domain.com
   ```

## Option 4: AWS SES (For Production)

If you're using AWS, SES is a cost-effective option.

### Steps:

1. **Set up AWS SES:**
   - Verify your email/domain in AWS SES
   - Create SMTP credentials

2. **Set Environment Variables:**
   ```
   MAIL_SERVER=email-smtp.region.amazonaws.com
   MAIL_PORT=587
   MAIL_USE_TLS=true
   MAIL_USERNAME=your-ses-smtp-username
   MAIL_PASSWORD=your-ses-smtp-password
   MAIL_DEFAULT_SENDER=your-verified-email@domain.com
   ```

## Testing Email Configuration

After setting up, test the forgot password feature:

1. Go to login page
2. Click "Forgot Password?"
3. Enter your email and role
4. Check your email inbox for the reset link

## Troubleshooting

### Email not sending?
- Check Render.com logs for email errors
- Verify all environment variables are set correctly
- Ensure SMTP credentials are correct
- Check if your email provider blocks SMTP from Render.com IPs

### Gmail not working?
- Make sure you're using an App Password, not your regular password
- Enable "Less secure app access" if App Passwords don't work (not recommended)
- Check if 2-Step Verification is enabled

### Fallback Behavior
If email sending fails, the application will show the reset link on the screen as a fallback, so password reset will still work.

## Security Notes

- Never commit email credentials to Git
- Use environment variables for all sensitive data
- Rotate passwords/API keys regularly
- Use App Passwords instead of main passwords when possible


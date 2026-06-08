# debug_email.py — put this in project root
import smtplib
import os
from dotenv import load_dotenv

load_dotenv()

sender       = os.getenv("GMAIL_ADDRESS")
app_password = os.getenv("GMAIL_APP_PASSWORD")

print(f"GMAIL_ADDRESS    : {sender}")
print(f"APP_PASSWORD SET : {'YES' if app_password else 'NO — check .env'}")
print(f"APP_PASSWORD LEN : {len(app_password) if app_password else 0} (should be 16)")

print("\n[1] Connecting to smtp.gmail.com:465 ...")
try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        print("[2] Connected ✓")

        print("[3] Logging in ...")
        server.login(sender, app_password)
        print("[4] Login successful ✓")

        print("[5] Sending test email ...")
        server.sendmail(
            sender,
            sender,   # send to yourself
            f"Subject: IncidentIQ Test\n\nIf you see this, email works."
        )
        print("[6] Email sent ✓ — check your inbox")

except smtplib.SMTPAuthenticationError:
    print("❌ AUTH FAILED — wrong app password or 2FA not enabled on Google account")

except smtplib.SMTPConnectError:
    print("❌ CONNECT FAILED — check internet or firewall blocking port 465")

except Exception as e:
    print(f"❌ UNEXPECTED ERROR: {type(e).__name__}: {e}")
import os
import sys

# ensure module path includes this directory
sys.path.insert(0, os.path.dirname(__file__))

from app import send_email

to = os.environ.get('TEST_RECIPIENT') or os.environ.get('EMAIL_ADDRESS')
if not to:
    print('No TEST_RECIPIENT or EMAIL_ADDRESS set in env; aborting')
    sys.exit(2)

subject = 'Notes Manager - SMTP test'
body = 'This is a test email sent by send_test_email.py to verify SMTP settings.'

ok = send_email(to, subject, body)
print('OK' if ok else 'FAILED')

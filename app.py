from flask import Flask, render_template,redirect, url_for, request, session, flash, send_file, jsonify
from werkzeug.utils import secure_filename
from database import (init_db, register_user,store_otp,
                      db_verify_otp,check_user_exists, login_user, db_reset_password,
                      db_add_note, get_user_notes, get_note,
                      db_update_note, db_delete_note, check_file_exists, db_upload_file, get_user_files, get_file, 
                      db_delete_file, search_notes, get_db_connection)
import re
import random
import smtplib
from email.message import EmailMessage
from itsdangerous import URLSafeTimedSerializer
import os
import io
import openpyxl
import traceback


app = Flask(__name__)
# Use environment-provided secret in production
app.secret_key = os.environ.get('SECRET_KEY', 'Notes manager')
# Use app-local uploads folder (absolute)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

serializer = URLSafeTimedSerializer(app.secret_key)

# Initialize DB inside app context (safe for Render/gunicorn)
with app.app_context():
    init_db()


# EMAIL CONFIGURATION (from env; optional)
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_SMTP_HOST = os.environ.get('EMAIL_SMTP_HOST', 'smtp.gmail.com')
EMAIL_SMTP_PORT = int(os.environ.get('EMAIL_SMTP_PORT', '587'))
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', '0') in ('1', 'true', 'True')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', '1') in ('1', 'true', 'True')
ENABLE_EMAIL_TEST = os.environ.get('ENABLE_EMAIL_TEST', '1') in ('1', 'true', 'True')
SHOW_OTP_ON_FAILURE = os.environ.get('SHOW_OTP_ON_FAILURE', '1') in ('1', 'true', 'True')




def send_email(to_mail, subject, body):
    """Send an email using configured SMTP settings.

    Returns True on success, False on failure. Non-fatal.
    """
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("Email not configured; skipping send")
        return False

    msg = EmailMessage()
    msg['To'] = to_mail
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg.set_content(body)

    try:
        if EMAIL_USE_SSL:
            with smtplib.SMTP_SSL(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, timeout=10) as smtp:
                smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, timeout=10) as smtp:
                smtp.ehlo()
                if EMAIL_USE_TLS:
                    smtp.starttls()
                    smtp.ehlo()
                smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                smtp.send_message(msg)
        return True
    except Exception as e:
        # Detailed logging to help debugging on Render: include SMTP config and traceback
        try:
            print('send_email error:', e)
            print('send_email config:', {
                'EMAIL_SMTP_HOST': EMAIL_SMTP_HOST,
                'EMAIL_SMTP_PORT': EMAIL_SMTP_PORT,
                'EMAIL_USE_SSL': EMAIL_USE_SSL,
                'EMAIL_USE_TLS': EMAIL_USE_TLS,
                'FROM': EMAIL_ADDRESS,
                'TO': to_mail,
            })
            print(traceback.format_exc())
        except Exception:
            # never raise from logging
            pass
        return False


@app.route('/email_test', methods=['GET', 'POST'])
def email_test():
    """Send a test email. Only enabled when ENABLE_EMAIL_TEST is truthy.

    GET: returns usage. POST: accepts form param `to` or uses `EMAIL_ADDRESS`.
    """
    if not ENABLE_EMAIL_TEST:
        return jsonify({'ok': False, 'error': 'email test disabled'}), 403

    to = request.values.get('to') or EMAIL_ADDRESS
    if not to:
        return jsonify({'ok': False, 'error': 'no recipient configured'}), 400

    subject = 'Test email from Notes Manager'
    body = 'This is a test email. If you received it, SMTP is configured.'
    ok = send_email(to, subject, body)
    if ok:
        return jsonify({'ok': True, 'to': to})
    return jsonify({'ok': False, 'error': 'send failed'})


@app.route('/email_diagnostics')
def email_diagnostics():
    """Return masked email/SMPP config and recent OTP rows for debugging.

    Enabled only when `ENABLE_EMAIL_TEST` is truthy to avoid exposing secrets in production.
    """
    if not ENABLE_EMAIL_TEST:
        return jsonify({'ok': False, 'error': 'disabled'}), 403

    def mask(s):
        if not s:
            return None
        try:
            parts = s.split('@')
            if len(parts) == 2:
                return parts[0][:2] + '***@' + parts[1]
        except Exception:
            pass
        return s[:2] + '***'

    # get recent OTPs
    otp_rows = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, user_id, otp, created_at FROM OTP ORDER BY id DESC LIMIT 10')
        for r in cur.fetchall():
            otp_rows.append({'id': r['id'], 'user_id': r['user_id'], 'otp': r['otp'], 'created_at': r['created_at']})
        conn.close()
    except Exception as e:
        print('email_diagnostics db error:', e)

    return jsonify({
        'ok': True,
        'email_from': mask(EMAIL_ADDRESS),
        'smtp_host': EMAIL_SMTP_HOST,
        'smtp_port': EMAIL_SMTP_PORT,
        'use_ssl': EMAIL_USE_SSL,
        'use_tls': EMAIL_USE_TLS,
        'recent_otps': otp_rows,
    })


@app.route('/resend_otp', methods=['GET', 'POST'])
def resend_otp():
    """Generate and resend an OTP to the given email.

    Accepts `email` as query param or form field. Stores OTP in DB and
    attempts to send it. On send failure, optionally stash `pending_otp`
    in session for display when `SHOW_OTP_ON_FAILURE` is enabled.
    """
    # accept from query string or POST body
    email = (request.values.get('email') or '').strip().lower()
    if not email:
        flash('Email is required to resend OTP', 'error')
        return redirect(url_for('register'))

    # ensure account exists
    if not check_user_exists(email):
        flash('Email not registered', 'error')
        return redirect(url_for('register'))

    # create and store OTP
    otp = str(random.randint(100000, 999999))
    try:
        store_otp(email, otp)
    except Exception as e:
        print('resend_otp store_otp error:', e)

    # attempt send
    sent = send_email(email, 'OTP Verification', f'Your OTP is: {otp}')
    if not sent:
        # if configured for debugging, expose OTP in session for display when SHOW_OTP_ON_FAILURE is enabled
        if SHOW_OTP_ON_FAILURE:
            session['pending_otp'] = otp
            flash('Failed to send OTP email; OTP displayed for debugging.', 'error')
        else:
            flash('Failed to send OTP email. Please contact admin.', 'error')
    else:
        flash('OTP resent to your email', 'success')

    return redirect(url_for('verify_otp', email=email))

@app.route('/')
def home():    
    return render_template('home.html')

@app.route('/register', methods = ['GET', 'POST'])
def register():    
    message = ''
    message_type = ''

    if request.method == "POST":
        username = request.form.get('username')
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password')

        if not username or not email or not password:
            message = "All fields required"
            message_type = "error"

        elif check_user_exists(email):
            message = "Email already exists"
            message_type = "error"

        else:
            success, message = register_user(username, email, password)

            if success:
                # ✅ Generate OTP
                otp = str(random.randint(100000, 999999))

                # ✅ Store OTP
                store_otp(email, otp)

                # ✅ Send email and handle failure paths
                sent = False
                try:
                    sent = send_email(
                        email,
                        "OTP Verification",
                        f"Your OTP is: {otp}"
                    )
                except Exception as e:
                    print("EMAIL ERROR:", e)

                # If sending failed and debugging is enabled, expose OTP in session
                if not sent:
                    if SHOW_OTP_ON_FAILURE:
                        session['pending_otp'] = otp
                        flash('Failed to send OTP email; OTP displayed for debugging.', 'error')
                    else:
                        flash('Failed to send OTP email. Please contact admin.', 'error')
                else:
                    flash('OTP sent to your email', 'success')

                return redirect(url_for('verify_otp', email=email))

            message_type = "error"

    return render_template('register.html', message=message, message_type=message_type)

@app.route('/verify_otp/<email>', methods = ['POST', 'GET'])
def verify_otp(email):
    print(email)
    message = ''
    message_type = ''
    # if OTP was stored in session because email sending failed, expose it to template
    otp_to_show = None
    if session.get('pending_otp'):
        otp_to_show = session.get('pending_otp')
    # show a resend link
    resend_url = url_for('resend_otp') + f"?email={email}"
    if request.method == 'POST':
        otp = request.form.get('otp')
        
        # normalize email for lookup
        norm_email = (email or '').strip().lower()
        if db_verify_otp(otp, norm_email):
            message = "OTP verified successfully"
            message_type = 'success'
            flash('OTP verified successfully. You may now login.', 'success')
            return redirect(url_for('login'))
        
        else:
            message = "Invalid OTP"
            message_type = 'error'
            
    # clear displayed otp after rendering once
    resp = render_template('verify_otp.html', email=email, message=message, message_type=message_type, otp_to_show=otp_to_show, resend_url=resend_url)
    if 'pending_otp' in session:
        session.pop('pending_otp', None)
    return resp
    
       
@app.route('/login', methods = ['POST', 'GET'])
def login():
    message = ''
    message_type = ''
    if request.method == 'POST':
        username = request.form.get('username',"")
        password = request.form.get('password', "")
        
        if not username or not password:
            message = "All fields are required!!"
            message_type = 'error'
            
        else:
            # normalize email if user provided email
            orig_username = username
            if '@' in (username or ''):
                username = username.strip().lower()
            success, message, user_id = login_user(username, password)
            message_type  = "success" if success else 'error'
            if success:
                session['username'] = username
                session['user_id'] = user_id
                return redirect(url_for('dashboard'))
            # if account not verified, redirect to verify page (prefill email)
            if message and 'not verified' in message.lower():
                # determine email to use for verification
                if '@' in (orig_username or ''):
                    email_for_verify = orig_username.strip().lower()
                else:
                    # try to look up email by username
                    try:
                        from database import get_email_by_username
                        email_for_verify = get_email_by_username(orig_username)
                    except Exception:
                        email_for_verify = None
                if email_for_verify:
                    # auto-generate and send OTP when user tries to login but account not verified
                    otp = str(random.randint(100000, 999999))
                    try:
                        store_otp(email_for_verify, otp)
                    except Exception as e:
                        print('login store_otp error:', e)

                    sent = False
                    try:
                        sent = send_email(email_for_verify, 'OTP Verification', f'Your OTP is: {otp}')
                    except Exception as e:
                        print('login send_email error:', e)

                    if not sent:
                        if SHOW_OTP_ON_FAILURE:
                            session['pending_otp'] = otp
                            flash('Failed to send OTP email; OTP displayed for debugging.', 'error')
                        else:
                            flash('Failed to send OTP email. Please contact admin.', 'error')
                    else:
                        flash('OTP sent to your email', 'success')

                    return redirect(url_for('verify_otp', email=email_for_verify))
            
    return render_template('login.html', message = message, message_type = message_type)


@app.route('/forgot_password', methods = ['POST', 'GET'])
def forgot_password():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        if not email:
            flash('Email is required','error')

        elif not check_user_exists(email):
            flash('Email not registered', 'error')

        else:
            token = serializer.dumps(email, salt = 'reset-password')
            reset_url = url_for('reset_password', token = token, _external = True)
            body = f"Click this link to reset your password: {reset_url}"
            try:
                sent = send_email(email, "Reset Link", body)
            except Exception as e:
                print('forgot_password send_email error:', e)
                sent = False

            if sent:
                flash("Reset link has been sent to registered email", 'success')
            else:
                flash("Failed to send reset link. Please contact admin.", 'error')
                           
    return render_template('forgot_password.html')
    
 
@app.route('/reset_password/<token>', methods = ['GET', 'POST'])
def reset_password(token) :
    try:
        email = serializer.loads(token, salt = 'reset-password', max_age=600)
    except Exception as e:
        print('reset_password token error:', e)
        flash('Reset link is invalid or has expired', 'error')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password')
        db_reset_password(email, password)
        flash('Password has been reset')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token = token)

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        return render_template('dashboard.html')
    return redirect(url_for('login'))

    
@app.route('/add_note', methods = ['GET', 'POST'])
def add_note(): 
    message = ''
    message_type = '' 
    if not 'user_id' in session:
        return redirect(url_for('login'))    

    if request.method == 'POST':
        title = request.form.get('title', '')
        content = request.form.get('content','')        
        
        if not title or not content:
            message = "All fields are required"
            message_type = 'error'            
        else:
            db_add_note(session['user_id'], title, content)
            message = "Added successfully"
            message_type = 'success'
            return redirect(url_for('view_notes'))
                             
    return render_template('add_note.html', message = message, message_type = message_type)

@app.route('/view_notes')
def view_notes():
    if not 'user_id' in session:
        return redirect(url_for('login'))
    notes = get_user_notes(session['user_id'])
    return render_template('view_notes.html', notes = notes)
        
@app.route('/view_note/<nid>')
def view_note(nid):
    if not 'user_id' in session:
        return redirect(url_for('login'))    
    note = get_note(nid)    
    return render_template('view_note.html',note = note )

@app.route('/update_note/<nid>', methods = ['GET', 'POST'])
def update_note(nid):
    if not 'user_id' in session:
        return redirect(url_for('login'))
    note = get_note(nid)
    message = ''
    message_type = ''
    if request.method == 'POST':
        new_title = request.form.get('title')
        new_content = request.form.get('content')        
        db_update_note(nid, new_title, new_content)
        message = 'Updated Successfully'
        message_type = 'success'
        note = {
            'title' : '',
            'content' : '',
            'created_at' : ''
        }                
    return render_template('update_note.html', note = note, message = message, message_type = message_type)

@app.route('/delete_note/<nid>')
def delete_note(nid):
    
    if not 'user_id' in session:
        return redirect(url_for('login'))
    
    db_delete_note(nid)
    message = "Deleted successfully"
    message_type = 'success'
    return render_template('view_notes.html', message = message, message_type = message_type)


@app.route('/upload_file', methods = ['GET', 'POST'])
def upload_file():    
    if not 'user_id' in session:
        return redirect(url_for('login'))
    message = ''
    message_type = ''       
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            message = "No file selected"
            message_type = 'error'
        else:
            filename = secure_filename(file.filename)
            if check_file_exists(session['user_id'], filename):
                message = "File already exists"
                message_type = 'error'
            else:
                # ensure upload folder exists
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    file.save(filepath)
                    db_upload_file(session['user_id'], filename, filepath)
                    flash('File uploaded successfully', 'success')
                    return redirect(url_for('view_files'))
                except Exception as e:
                    message = 'Failed to save file'
                    message_type = 'error'
                    print(f"[upload_file] save error: {e}")
    return render_template('upload_file.html', message = message, message_type = message_type)


@app.route('/view_files')
def view_files():    
    if not 'user_id' in session:
        return redirect(url_for('login'))
    files = get_user_files(session['user_id'])
    return render_template('view_files.html', files = files)

@app.route('/view_file/<fid>')
def view_file(fid):
    if not 'user_id'in session:
        return redirect(url_for('login'))
    file = get_file(fid)
    if not file:
        flash('File not found', 'error')
        return redirect(url_for('view_files'))
    if not os.path.exists(file):
        flash('File missing on server', 'error')
        return redirect(url_for('view_files'))
    return send_file(file, as_attachment = False)

@app.route('/delete_file/<fid>')
def delete_file(fid):
    if not 'user_id' in session:
        return redirect(url_for('login'))
    file = get_file(fid)
    # remove DB record first
    db_delete_file(fid, session['user_id'])
    # then remove file if it exists
    if file and os.path.exists(file):
        try:
            os.remove(file)
        except Exception:
            flash('Failed to remove file from disk', 'error')
    else:
        flash('File not found on server', 'error')
    return redirect(url_for('view_files'))

@app.route('/download_file/<fid>')
def download_file(fid):
    if not 'user_id'in session:
        return redirect(url_for('login'))
    file = get_file(fid)
    if not file or not os.path.exists(file):
        flash('File not available for download', 'error')
        return redirect(url_for('view_files'))
    return send_file(file, as_attachment = True)



@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    message = ""
    message_type = '' 
    notes = ''
    if request.method == "POST":
        query = request.form.get('query','')
        
        if not query:
            message = "Invalid search parameters"
            message_type = 'error'
            
        else:
            notes = search_notes(query, session['user_id'])
                             
    return render_template('search.html', message = message, message_type = message_type, notes = notes )

@app.route('/export_notes')
def export_notes():
    if 'user_id' not in session:
        return redirect(url_for('login'))   
    notes = get_user_notes(session['user_id'])
    data = [["Title", 'Content', 'Created_at']]
    for i in notes:
        data.append([i['title'], i['content'], i['created_at']])        
    output = io.BytesIO()
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    for row in data:
        sheet.append(row)      
    workbook.save(output)  
    output.seek(0)    
    return send_file(output, as_attachment= True,download_name= "exported_notes.xlsx")
    


@app.route('/logout')
def logout():
    
    if 'user_id' in session :
        session.clear()
        
        return redirect(url_for('login'))

# if __name__ == "__main__":
#     # Run DB only in local
#     if os.environ.get("ENV") != "production":
#         init_db()

#     port = int(os.environ.get("PORT", 5000))
#     app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)  # run always once

# from flask import Flask, render_template, redirect, url_for, request, session, flash, send_file
# from werkzeug.utils import secure_filename
# from database import (
#     init_db, register_user, store_otp,
#     db_verify_otp, check_user_exists, login_user, db_reset_password,
#     db_add_note, get_user_notes, get_note,
#     db_update_note, db_delete_note, check_file_exists,
#     db_upload_file, get_user_files, get_file,
#     db_delete_file, search_notes
# )

# import re
# import random
# import smtplib
# from email.message import EmailMessage
# from itsdangerous import URLSafeTimedSerializer
# import os
# import io
# import openpyxl

# app = Flask(__name__)
# # secrets from env for production; fallback for local dev
# app.secret_key = os.environ.get('SECRET_KEY', 'Notes manager')
# app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
# os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# serializer = URLSafeTimedSerializer(app.secret_key)

# # ✅ SAFE DB INIT (important for Render)
# with app.app_context():
#     init_db()

# # ================= EMAIL CONFIG =================
# EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
# EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')


# def send_email(to_mail, subject, body):
#     # Non-fatal: log and continue on failure
#     if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
#         print("Email not configured; skipping send")
#         return False
#     try:
#         msg = EmailMessage()
#         msg['To'] = to_mail
#         msg['Subject'] = subject
#         msg['From'] = EMAIL_ADDRESS
#         msg.set_content(body)

#         with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as smtp:
#             smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
#             smtp.send_message(msg)
#         return True
#     except Exception as e:
#         print("send_email error:", e)
#         return False

# # ================= ROUTES =================

# @app.route('/')
# def home():
#     return render_template('home.html')

# # ================= REGISTER =================
# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     message = ''
#     message_type = ''

#     if request.method == "POST":
#         username = request.form.get('username', '').strip()
#         mail = request.form.get('email', '').lower()
#         password = request.form.get('password', '')

#         if not username or not mail or not password:
#             message = "Enter all details"
#             message_type = 'error'

#         elif not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', mail):
#             message = "Invalid email"
#             message_type = 'error'

#         elif len(password) < 6:
#             message = "Password must be 6+ chars"
#             message_type = "error"

#         elif check_user_exists(mail):
#             message = "Email already exists"
#             message_type = 'error'

#         else:
#             success, message = register_user(username, mail, password)
#             message_type = "success"

#             if success:
#                 otp = str(random.randint(100000, 999999))
#                 store_otp(mail, otp)
#                 send_email(mail, "OTP", f"Your OTP is {otp}")
#                 return redirect(url_for('verify_otp', email=mail))

#     return render_template('register.html', message=message, message_type=message_type)

# # ================= OTP =================
# @app.route('/verify_otp/<email>', methods=['GET', 'POST'])
# def verify_otp(email):
#     message = ''
#     message_type = ''

#     if request.method == 'POST':
#         otp = request.form.get('otp')

#         try:
#             if db_verify_otp(otp, email):
#                 return redirect(url_for('login'))
#         except Exception as e:
#             print("verify_otp error:", e)
#             message = "Server error"
#             message_type = 'error'
#         else:
#             message = "Invalid OTP"
#             message_type = 'error'

#     return render_template('verify_otp.html', email=email, message=message, message_type=message_type)

# # ================= LOGIN =================
# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     message = ''
#     message_type = ''

#     if request.method == 'POST':
#         username = request.form.get('username', "")
#         password = request.form.get('password', "")

#         success, message, user_id = login_user(username, password)
#         message_type = "success" if success else "error"

#         if success:
#             session['username'] = username
#             session['user_id'] = user_id
#             return redirect(url_for('dashboard'))

#     return render_template('login.html', message=message, message_type=message_type)

# # ================= FORGOT PASSWORD =================
# @app.route('/forgot_password', methods=['GET', 'POST'])
# def forgot_password():
#     if request.method == 'POST':
#         email = request.form.get('email')

#         if not email:
#             flash("Email required", "error")

#         elif not check_user_exists(email):
#             flash("Email not found", "error")

#         else:
#             token = serializer.dumps(email, salt='reset-password')
#             reset_url = url_for('reset_password', token=token, _external=True)
#             sent = send_email(email, "Reset Password", f"Click: {reset_url}")
#             if sent:
#                 flash("Reset link sent", "success")
#             else:
#                 flash("Failed to send reset link", "error")

#     return render_template('forgot_password.html')

# # ================= RESET PASSWORD =================
# @app.route('/reset_password/<token>', methods=['GET', 'POST'])
# def reset_password(token):
#     try:
#         email = serializer.loads(token, salt='reset-password', max_age=600)
#     except Exception:
#         flash("Link expired", "error")
#         return redirect(url_for('forgot_password'))

#     if request.method == 'POST':
#         password = request.form.get('password')
#         ok = db_reset_password(email, password)
#         if ok:
#             flash("Password reset success")
#             return redirect(url_for('login'))
#         flash("Failed to reset password", 'error')

#     return render_template('reset_password.html')

# # ================= DASHBOARD =================
# @app.route('/dashboard')
# def dashboard():
#     if 'user_id' in session:
#         return render_template('dashboard.html')
#     return redirect(url_for('login'))

# # ================= NOTES =================
# @app.route('/add_note', methods=['GET', 'POST'])
# def add_note():
#     if 'user_id' not in session:
#         return redirect(url_for('login'))

#     if request.method == 'POST':
#         try:
#             db_add_note(session['user_id'],
#                         request.form.get('title'),
#                         request.form.get('content'))
#         except Exception as e:
#             print("add_note error:", e)
#         return redirect(url_for('view_notes'))

#     return render_template('add_note.html')

# @app.route('/view_notes')
# def view_notes():
#     if 'user_id' not in session:
#         return redirect(url_for('login'))
#     try:
#         notes = get_user_notes(session['user_id']) or []
#         return render_template('view_notes.html', notes=notes)
#     except Exception as e:
#         print("ERROR in view_notes:", e)
#         return "Internal Server Error", 500


# @app.route('/view_note/<nid>')
# def view_note(nid):
#     if 'user_id' not in session:
#         return redirect(url_for('login'))
#     try:
#         note = get_note(nid)
#         if not note:
#             flash('Note not found', 'error')
#             return redirect(url_for('view_notes'))
#         return render_template('view_note.html', note=note)
#     except Exception as e:
#         print('view_note error:', e)
#         return "Internal Server Error", 500


# @app.route('/update_note/<nid>', methods=['GET', 'POST'])
# def update_note(nid):
#     if 'user_id' not in session:
#         return redirect(url_for('login'))
#     try:
#         note = get_note(nid)
#         if request.method == 'POST':
#             new_title = request.form.get('title', '')
#             new_content = request.form.get('content', '')
#             ok = db_update_note(nid, new_title, new_content)
#             if ok:
#                 flash('Updated successfully', 'success')
#             else:
#                 flash('Failed to update', 'error')
#             return redirect(url_for('view_notes'))
#         return render_template('update_note.html', note=note)
#     except Exception as e:
#         print('update_note error:', e)
#         return "Internal Server Error", 500

# @app.route('/delete_note/<nid>')
# def delete_note(nid):
#     if 'user_id' not in session:
#         return redirect(url_for('login'))
#     try:
#         db_delete_note(nid)
#     except Exception as e:
#         print("delete_note error:", e)
#     return redirect(url_for('view_notes'))

# # ================= FILE UPLOAD =================
# @app.route('/upload_file', methods=['GET', 'POST'])
# def upload_file():
#     if 'user_id' not in session:
#         return redirect(url_for('login'))

#     def allowed_file(filename):
#         allowed = {'.txt', '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.xlsx', '.csv'}
#         _, ext = os.path.splitext(filename.lower())
#         return ext in allowed

#     if request.method == 'POST':
#         file = request.files.get('file')

#         if not file or not file.filename:
#             flash('No file selected', 'error')
#             return render_template('upload_file.html')

#         filename = secure_filename(file.filename)
#         if not allowed_file(filename):
#             flash('File type not allowed', 'error')
#             return render_template('upload_file.html')

#         filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#         try:
#             file.save(filepath)
#             db_upload_file(session['user_id'], filename, filepath)
#             flash('File uploaded', 'success')
#             return redirect(url_for('view_files'))
#         except Exception as e:
#             print('upload_file save error:', e)
#             flash('Failed to save file', 'error')
#             return render_template('upload_file.html')

#     return render_template('upload_file.html')

# @app.route('/view_files')
# def view_files():
#     if 'user_id' not in session:
#         return redirect(url_for('login'))
#     try:
#         files = get_user_files(session['user_id'])
#     except Exception as e:
#         print('view_files error:', e)
#         files = []
#     return render_template('view_files.html', files=files)

# # ================= SEARCH =================
# @app.route('/search', methods=['GET', 'POST'])
# def search():
#     if 'user_id' not in session:
#         return redirect(url_for('login'))
#     notes = []
#     if request.method == "POST":
#         q = request.form.get('query', '')
#         if q:
#             notes = search_notes(q, session['user_id'])
#     return render_template('search.html', notes=notes)

# # ================= EXPORT =================
# @app.route('/export_notes')
# def export_notes():
#     if 'user_id' not in session:
#         return redirect(url_for('login'))
#     notes = get_user_notes(session['user_id'])
#     output = io.BytesIO()

#     wb = openpyxl.Workbook()
#     sheet = wb.active

#     for n in notes:
#         sheet.append([n['title'], n['content'], n['created_at']])

#     wb.save(output)
#     output.seek(0)

#     return send_file(output, as_attachment=True, download_name="notes.xlsx")

# # ================= LOGOUT =================
# @app.route('/logout')
# def logout():
#     session.clear()
#     return redirect(url_for('login'))

# # ================= RUN =================
# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 5000))
#     app.run(host="0.0.0.0", port=port)
from flask import Flask, render_template,redirect, url_for, request, session, flash, send_file
from werkzeug.utils import secure_filename
from database import (init_db, register_user,store_otp,
                      db_verify_otp,check_user_exists, login_user, db_reset_password,
                      db_add_note, get_user_notes, get_note,
                      db_update_note, db_delete_note, check_file_exists, db_upload_file, get_user_files, get_file, 
                      db_delete_file, search_notes)
import re
import random
import smtplib
from email.message import EmailMessage
from itsdangerous import URLSafeTimedSerializer
import os
import io
import openpyxl


app = Flask(__name__)
app.secret_key = 'Notes manager'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok = True)

serializer = URLSafeTimedSerializer(app.secret_key)

init_db()

#EMAIL CONFIGURATION
EMAIL_ADDRESS = "pythonexample704@gmail.com"
EMAIL_PASSWORD = 'fftg prnw vwyo zhoe'
def send_email(to_mail, subject, body):
    msg = EmailMessage()
    msg['To'] = to_mail
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg.set_content(body)
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

@app.route('/')
def home():    
    return render_template('home.html')

@app.route('/register', methods = ['GET', 'POST'])
def register():    
    if request.method == "POST": 
        
        message = ''
        message_type = ''       
        username = request.form.get('username', '').strip()
        mail = request.form.get('email', '').lower()
        password = request.form.get('password','')    
        if not username or not mail or not password:
            message = "Enter all the details"
            message_type = 'error'
            
        elif not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', mail):
            message = "Enter a valid email id"
            message_type = 'error'
                                  
        elif len(password) < 6:
            message = "Enter atleast 6 characters password"
            message_type = "error" 
            
        elif check_user_exists(mail):
            message = "Email already exists!!"
            message_type = 'error'
            
        else:
            success, message = register_user(username, mail, password)
            message_type = "success"
            
            if success:
                otp = str(random.randint(100000, 999999))
                store_otp(mail, otp)
                subject = "OTP for Notes manager"
                body = f"Your OTP for Notes manager is {otp}"
                send_email(mail, subject, body)
                
                return redirect(url_for('verify_otp', email = mail))
                    
                                    
        return render_template('register.html', message = message, message_type = message_type)
                
    return render_template('register.html')

@app.route('/verify_otp/<email>', methods = ['POST', 'GET'])
def verify_otp(email):
    print(email)
    message = ''
    message_type = ''
    if request.method == 'POST':
        otp = request.form.get('otp')
        
        if db_verify_otp(otp,email):
            message = "OTP verified successfully"
            message_type = 'success'
            return redirect(url_for('login'))
        
        else:
            message = "Invalid OTP"
            message_type = 'error'
            
    return render_template('verify_otp.html',email = email, message = message, message_type= message_type)
    
       
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
            success, message, user_id = login_user(username, password)
            message_type  = "success" if success else 'error'
            if success:                
                session['username'] = username
                session['user_id'] = user_id
                
                return redirect(url_for('dashboard'))
            
    return render_template('login.html', message = message, message_type = message_type)


@app.route('/forgot_password', methods = ['POST', 'GET'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')        
        if not email:
            flash('Email is required','error')
            
        elif not check_user_exists(email):
            flash('Email not registered', 'error')
            
        else:
            token = serializer.dumps(email, salt = 'reset-password')
            reset_url = url_for('reset_password', token = token, _external = True)
            body = f"Click this link to reset your password: {reset_url}"
            send_email(email, "Reset Link", body)
            flash("Reset link has been sent to registered email", 'success')
                           
    return render_template('forgot_password.html')
    
 
@app.route('/reset_password/<token>', methods = ['GET', 'POST'])
def reset_password(token) :
    email = serializer.loads(token, salt = 'reset-password', max_age= 600)
    
    if request.method == 'POST':
        password = request.form.get('password')
        db_reset_password(email, password)
        flash('Password has been reset')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', token = token)

@app.route('/dashborad')
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


app.run(debug = "True", port = 5008)




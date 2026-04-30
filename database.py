import pymysql
import pymysql.cursors

db_config = {
    'host' : 'localhost',
    'user': 'root',
    'password': 'root',
    'database' : 'notes_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

#for establishing databse connection
def get_db_connection():    
    conn = pymysql.connect(**db_config)
    
    return conn

#initialising database
def init_db():
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS User
                   (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(30) NOT NULL,
                    email VARCHAR(30) UNIQUE NOT NULL,
                    password VARCHAR(30) NOT NULL,
                    otp VARCHAR(6)
                    )'''
        
    )
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS Notes
        (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            title VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES User(id) ON DELETE CASCADE
        )
        '''
    )
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS File_Upload(
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            filename VARCHAR(100) NOT NULL,
            filepath VARCHAR(100) NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    
   
    
    conn.commit()
    cursor.close()
    conn.close()
    
#storing user details
def register_user(username, email, password):    
    conn = get_db_connection()
    cursor = conn.cursor()      
    cursor.execute(
        '''
        INSERT INTO User (username, email, password)
        VALUES
        (%s, %s, %s)''', (username, email, password)        
    )   
    conn.commit()
    cursor.close()
    conn.close()    
    return True, "Registration successful!, Please check your mail for OTP"

#storing otp sent to user
def store_otp(email, otp):    
    conn = get_db_connection()
    cursor = conn.cursor()
    email = email
    otp = otp
    cursor.execute(
        '''
        UPDATE User SET otp = %s where email = %s
        ''', (otp, email)
    )    
    conn.commit()
    cursor.close()
    conn.close()
    
#checking duplicate email
def check_user_exists(email):
    
    conn = get_db_connection()
    cursor = conn.cursor()    
    cursor.execute(
        '''
        SELECT * from User WHERE email = %s
        ''', (email,)
    )    
    user = cursor.fetchone()    
    cursor.close()
    conn.close()    
    return bool(user)
  
#for verifying OTP 
def db_verify_otp(user_otp, email):
     conn = get_db_connection()
     cursor = conn.cursor()
     user_otp = user_otp
     email = email
     print(user_otp, email)
     cursor.execute(
         '''
         SELECT * from User where otp = %s and email = %s
         ''', (user_otp, email)
     )
     user = cursor.fetchone()
     if user:
        cursor.execute(
            '''
            UPDATE User set otp = %s where email = %s
            ''', ('NULL',email )
        )
        conn.commit()
     cursor.close()
     conn.close()
     
     return bool(user)
     
 
def login_user(username, password):    
    conn = get_db_connection()
    cursor = conn.cursor()    
    cursor.execute(
        '''
        SELECT * from User where username = %s and password = %s
         ''',(username, password)
    )      
    user = cursor.fetchone()
    cursor.close()
    conn.close()    
    if user:
        return True, "Login Successful!!", user['id']
    
    return False, "Invalid Credentials", None
    
  
     
def db_reset_password(email, password):
    email = email.strip().lower()
    print(f"[DB] Resetting password for email: '{email}'")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE User SET password = %s WHERE email = %s
    ''', (password, email))
    conn.commit()
    cursor.close()
    conn.close()
    
def db_reset_password(email, password):
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        '''UPDATE User SET password = %s where email = %s
        ''', (password, email)
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    
  
def db_add_note(user_id, title, content) :
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        '''
        INSERT INTO Notes (user_id, title, content)
        VALUES
        (%s, %s, %s)
        ''', (user_id, title, content)
    ) 
    
    conn.commit()
    cursor.close()
    conn.close()

def get_user_notes(user_id):
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        '''
        SELECT * from Notes where user_id = %s
        ''', (user_id,)
    )
    notes = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return notes

def get_note(nid):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT * FROM Notes WHERE id = %s
        ''', (nid,)
    )
    
    note = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return note

def db_update_note(nid,new_title, new_content):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''UPDATE Notes SET title = %s, content = %s wHERE id = %s
        ''', (new_title, new_content, nid)
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    
def db_delete_note(nid):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        '''
        DELETE from Notes where id = %s
        ''',(nid)
    )  
    
    conn.commit()
    cursor.close()
    conn.close()


def db_upload_file(user_id, filename, filepath):
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        '''
        INSERT INTO File_Upload (user_id, filename, filepath)
        VALUES
        (%s, %s, %s)
        ''', (user_id,filename,filepath)
    )
    conn.commit()
    cursor.close()
    conn.close()
    
def check_file_exists(user_id, filename):
    
    conn = get_db_connection()
    cursor = conn.cursor()    
    cursor.execute(
        '''
        SELECT * from File_Upload where user_id = %s and filename = %s
        ''', (user_id, filename)
    )
    
    file = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if file:
        return True
    return False
    
    
def get_user_files(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM File_Upload WHERE user_id = %s
    ''', (user_id,))
    files = cursor.fetchall()
    cursor.close()
    conn.close()
    return files

def get_file (fid):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        ''' SELECT * from File_Upload where id = %s
        ''', (fid,)
    )
    
    file = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return file['filepath']

def db_delete_file(fid, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM File_Upload WHERE id = %s AND user_id = %s
    ''', (fid, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    return True, "File deleted successfully!"

def search_notes(query, user_id):
    conn =  get_db_connection()
    cursor = conn.cursor()
    query = query
    user_id = user_id
    cursor.execute(
        '''
        SELECT * FROM Notes WHERE user_id = %s and title LIKE %s
        ''', (user_id, f'%{query}%')
    )  
    notes = cursor.fetchall()
    cursor.close()
    conn.close()        
    return notes
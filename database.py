import os
import pymysql
from pymysql.cursors import DictCursor

# Environment-based configuration
# Supports local development and production (e.g. PythonAnywhere).
import os

ENV = os.environ.get("ENV")

if ENV == "production":
    db_config = {
        "host": "sandhyachirumamilla.mysql.pythonanywhere-services.com",
        "user": "sandhyachirumamilla",
        "password": os.environ.get("Sandhya@123"),
        "database": "sandhyachirumamilla$notes_db"
    }
else:
    db_config = {
        "host": "localhost",
        "user": "root",
        "password": "root",
        "database": "notes_db"
    }


def get_db_connection():
    """Create and return a new pymysql connection using DictCursor.

    Caller is responsible for closing the connection. Use try/finally.
    """
    # Resolve DB configuration at call-time from environment with sensible
    # fallbacks. This avoids NameError during autoreload if module-level
    # variables are not yet (re)bound.
    if ENV == "production":
        host = os.environ.get("DB_HOST") or "sandhyachirumamilla.mysql.pythonanywhere-services.com"
        user = os.environ.get("DB_USER") or "sandhyachirumamilla"
        dbname = os.environ.get("DB_NAME") or "sandhyachirumamilla$notes_db"
    else:
        host = os.environ.get("DB_HOST") or "localhost"
        user = os.environ.get("DB_USER") or "root"
        dbname = os.environ.get("DB_NAME") or "notes_db"

    password = os.environ.get("Sandhya@123") or "root"

    conn = pymysql.connect(host=host,
                           user=user,
                           password=password,
                           database=dbname,
                           cursorclass=DictCursor,
                           charset="utf8mb4",
                           autocommit=False)
    return conn


def init_db():
    """Create required tables if they don't exist.

    Columns sized to avoid DataError for normal use (email/password lengths).
    """
    create_users = """
    CREATE TABLE IF NOT EXISTS User (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) NOT NULL,
        email VARCHAR(255) NOT NULL UNIQUE,
        password VARCHAR(128) NOT NULL,
        otp VARCHAR(10),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    create_notes = """
    CREATE TABLE IF NOT EXISTS Notes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        title VARCHAR(200) NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES User(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    create_files = """
    CREATE TABLE IF NOT EXISTS File_Upload (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        filename VARCHAR(255) NOT NULL,
        filepath VARCHAR(1024) NOT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES User(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    try:
        conn = get_db_connection()
    except pymysql.MySQLError as e:
        print(f"[init_db] Could not connect to database: {e}\nSkipping DB initialization. Set DB env vars to enable DB access.")
        return

    try:
        cursor = conn.cursor()
        cursor.execute(create_users)
        cursor.execute(create_notes)
        cursor.execute(create_files)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[init_db] Error creating tables: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def register_user(username, email, password):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO User (username, email, password) VALUES (%s, %s, %s)",
            (username, email, password),
        )
        conn.commit()
        return True, "Registration successful! Please check your mail for OTP"
    except pymysql.IntegrityError as e:
        conn.rollback()
        # likely duplicate email
        return False, "Email already registered"
    except Exception as e:
        conn.rollback()
        print(f"[register_user] Error: {e}")
        return False, "Registration failed"
    finally:
        cursor.close()
        conn.close()


def store_otp(email, otp):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE User SET otp = %s WHERE email = %s", (otp, email))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"[store_otp] Error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def check_user_exists(email):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM User WHERE email = %s", (email,))
        user = cursor.fetchone()
        return bool(user)
    except Exception as e:
        print(f"[check_user_exists] Error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def db_verify_otp(user_otp, email):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM User WHERE otp = %s AND email = %s", (user_otp, email))
        user = cursor.fetchone()
        if user:
            cursor.execute("UPDATE User SET otp = NULL WHERE email = %s", (email,))
            conn.commit()
            return True
        return False
    except Exception as e:
        conn.rollback()
        print(f"[db_verify_otp] Error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def login_user(username_or_email, password):
    """Attempt to authenticate a user by username or email.

    Returns: (success: bool, message: str, user_id: int|None)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # allow login via username OR email
        cursor.execute(
            "SELECT id, username, email FROM User WHERE (username = %s OR email = %s) AND password = %s",
            (username_or_email, username_or_email, password),
        )
        user = cursor.fetchone()
        if user:
            return True, "Login successful", user.get("id")
        return False, "Invalid credentials", None
    except Exception as e:
        print(f"[login_user] Error: {e}")
        return False, "Login failed due to server error", None
    finally:
        cursor.close()
        conn.close()


def db_reset_password(email, password):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE User SET password = %s WHERE email = %s", (password, email))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"[db_reset_password] Error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def db_add_note(user_id, title, content):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Notes (user_id, title, content) VALUES (%s, %s, %s)", (user_id, title, content))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"[db_add_note] Error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def get_user_notes(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Notes WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        return cursor.fetchall()
    except Exception as e:
        print(f"[get_user_notes] Error: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def get_note(nid):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Notes WHERE id = %s", (nid,))
        return cursor.fetchone()
    except Exception as e:
        print(f"[get_note] Error: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


def db_update_note(nid, new_title, new_content):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Notes SET title = %s, content = %s WHERE id = %s", (new_title, new_content, nid))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"[db_update_note] Error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def db_delete_note(nid):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Notes WHERE id = %s", (nid,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"[db_delete_note] Error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def db_upload_file(user_id, filename, filepath):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO File_Upload (user_id, filename, filepath) VALUES (%s, %s, %s)", (user_id, filename, filepath))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"[db_upload_file] Error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def check_file_exists(user_id, filename):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM File_Upload WHERE user_id = %s AND filename = %s", (user_id, filename))
        return bool(cursor.fetchone())
    except Exception as e:
        print(f"[check_file_exists] Error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def get_user_files(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM File_Upload WHERE user_id = %s ORDER BY uploaded_at DESC", (user_id,))
        return cursor.fetchall()
    except Exception as e:
        print(f"[get_user_files] Error: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def get_file(fid):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM File_Upload WHERE id = %s", (fid,))
        file = cursor.fetchone()
        if not file:
            return None
        filepath = file.get("filepath")
        if not filepath:
            return None
        # return absolute path so send_file/os.path checks succeed
        return os.path.abspath(filepath)
    except Exception as e:
        print(f"[get_file] Error: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


def db_delete_file(fid, user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM File_Upload WHERE id = %s AND user_id = %s", (fid, user_id))
        conn.commit()
        return True, "File deleted successfully!"
    except Exception as e:
        conn.rollback()
        print(f"[db_delete_file] Error: {e}")
        return False, "Failed to delete file"
    finally:
        cursor.close()
        conn.close()


def search_notes(query, user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Notes WHERE user_id = %s AND title LIKE %s", (user_id, f"%{query}%"))
        return cursor.fetchall()
    except Exception as e:
        print(f"[search_notes] Error: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

# import os
# import pymysql
# from pymysql.cursors import DictCursor

# # Environment-based configuration
# # Supports local development and production (e.g. PythonAnywhere).
# import os

# ENV = os.environ.get("ENV")

# if ENV == "production":
#     db_config = {
#         "host": "sandhyachirumamilla.mysql.pythonanywhere-services.com",
#         "user": "sandhyachirumamilla",
#         "password": os.environ.get("DB_PASSWORD") or "Sandhya@123",
#         "database": "sandhyachirumamilla$notes_db"
#     }
# else:
#     db_config = {
#         "host": "localhost",
#         "user": "root",
#         "password": "root",
#         "database": "notes_db"
#     }


# def get_db_connection():
#     """Create and return a new pymysql connection using DictCursor.

#     Caller is responsible for closing the connection. Use try/finally.
#     """
#     # Resolve DB configuration at call-time from environment with sensible
#     # fallbacks. This avoids NameError during autoreload if module-level
#     # variables are not yet (re)bound.
#     if ENV == "production":
#         host = os.environ.get("DB_HOST") or "sandhyachirumamilla.mysql.pythonanywhere-services.com"
#         user = os.environ.get("DB_USER") or "sandhyachirumamilla"
#         dbname = os.environ.get("DB_NAME") or "sandhyachirumamilla$notes_db"
#     else:
#         host = os.environ.get("DB_HOST") or "localhost"
#         user = os.environ.get("DB_USER") or "root"
#         dbname = os.environ.get("DB_NAME") or "notes_db"

#     password = os.environ.get("DB_PASSWORD") or "Sandhya@123"

#     conn = pymysql.connect(host=host,
#                            user=user,
#                            password='root' if ENV != "production" else password,
#                            database=dbname,
#                            cursorclass=DictCursor,
#                            charset="utf8mb4",
#                            autocommit=False)
#     return conn


# def init_db():
#     """Create required tables if they don't exist.

#     Columns sized to avoid DataError for normal use (email/password lengths).
#     """
#     create_users = """
#     CREATE TABLE IF NOT EXISTS User (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         username VARCHAR(50) NOT NULL,
#         email VARCHAR(255) NOT NULL UNIQUE,
#         password VARCHAR(128) NOT NULL,
#         otp VARCHAR(10),
#         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#     ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
#     """

#     create_notes = """
#     CREATE TABLE IF NOT EXISTS Notes (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         user_id INT NOT NULL,
#         title VARCHAR(200) NOT NULL,
#         content TEXT NOT NULL,
#         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#         FOREIGN KEY (user_id) REFERENCES User(id) ON DELETE CASCADE
#     ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
#     """

#     create_files = """
#     CREATE TABLE IF NOT EXISTS File_Upload (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         user_id INT NOT NULL,
#         filename VARCHAR(255) NOT NULL,
#         filepath VARCHAR(1024) NOT NULL,
#         uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#         FOREIGN KEY (user_id) REFERENCES User(id) ON DELETE CASCADE
#     ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
#     """

#     try:
#         conn = get_db_connection()
#     except pymysql.MySQLError as e:
#         print(f"[init_db] Could not connect to database: {e}\nSkipping DB initialization. Set DB env vars to enable DB access.")
#         return

#     try:
#         cursor = conn.cursor()
#         cursor.execute(create_users)
#         cursor.execute(create_notes)
#         cursor.execute(create_files)
#         conn.commit()
#     except Exception as e:
#         conn.rollback()
#         print(f"[init_db] Error creating tables: {e}")
#         raise
#     finally:
#         cursor.close()
#         conn.close()


# def register_user(username, email, password):
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute(
#             "INSERT INTO User (username, email, password) VALUES (%s, %s, %s)",
#             (username, email, password),
#         )
#         conn.commit()
#         return True, "Registration successful! Please check your mail for OTP"
#     except pymysql.IntegrityError:
#         if conn:
#             conn.rollback()
#         return False, "Email already registered"
#     except Exception as e:
#         if conn:
#             conn.rollback()
#         print(f"[register_user] Error: {e}")
#         return False, "Registration failed"
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# def store_otp(email, otp):
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("UPDATE User SET otp = %s WHERE email = %s", (otp, email))
#         conn.commit()
#         return True
#     except Exception as e:
#         if conn:
#             conn.rollback()
#         print(f"[store_otp] Error: {e}")
#         return False
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# def check_user_exists(email):
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT id FROM User WHERE email = %s", (email,))
#         user = cursor.fetchone()
#         return bool(user)
#     except Exception as e:
#         print(f"[check_user_exists] Error: {e}")
#         return False
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# def db_verify_otp(user_otp, email):
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT id FROM User WHERE otp = %s AND email = %s", (user_otp, email))
#         user = cursor.fetchone()
#         if user:
#             cursor.execute("UPDATE User SET otp = NULL WHERE email = %s", (email,))
#             conn.commit()
#             return True
#         return False
#     except Exception as e:
#         if conn:
#             conn.rollback()
#         print(f"[db_verify_otp] Error: {e}")
#         return False
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# def login_user(username_or_email, password):
#     """Attempt to authenticate a user by username or email.

#     Returns: (success: bool, message: str, user_id: int|None)
#     """
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # allow login via username OR email
#         cursor.execute(
#             "SELECT id, username, email FROM User WHERE (username = %s OR email = %s) AND password = %s",
#             (username_or_email, username_or_email, password),
#         )
#         user = cursor.fetchone()
#         if user:
#             return True, "Login successful", user.get("id")
#         return False, "Invalid credentials", None
#     except Exception as e:
#         print(f"[login_user] Error: {e}")
#         return False, "Login failed due to server error", None
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# def db_reset_password(email, password):
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("UPDATE User SET password = %s WHERE email = %s", (password, email))
#         conn.commit()
#         return True
#     except Exception as e:
#         if conn:
#             conn.rollback()
#         print(f"[db_reset_password] Error: {e}")
#         return False
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# def db_add_note(user_id, title, content):
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("INSERT INTO Notes (user_id, title, content) VALUES (%s, %s, %s)", (user_id, title, content))
#         conn.commit()
#         return True
#     except Exception as e:
#         if conn:
#             conn.rollback()
#         print(f"[db_add_note] Error: {e}")
#         return False
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# def get_user_notes(user_id):
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Notes WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
#         return cursor.fetchall()
#     except Exception as e:
#         print(f"[get_user_notes] Error: {e}")
#         return []
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# def get_note(nid):
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Notes WHERE id = %s", (nid,))
#         return cursor.fetchone()
#     except Exception as e:
#         print(f"[get_note] Error: {e}")
#         return None
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# def db_update_note(nid, new_title, new_content):
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("UPDATE Notes SET title = %s, content = %s WHERE id = %s", (new_title, new_content, nid))
#         conn.commit()
#         return True
#     except Exception as e:
#         if conn:
#             conn.rollback()
#         print(f"[db_update_note] Error: {e}")
#         return False
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# def db_delete_note(nid):
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM Notes WHERE id = %s", (nid,))
#         conn.commit()
#         return True
#     except Exception as e:
#         if conn:
#             conn.rollback()
#         print(f"[db_delete_note] Error: {e}")
#         return False
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# def db_upload_file(user_id, filename, filepath):
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("INSERT INTO File_Upload (user_id, filename, filepath) VALUES (%s, %s, %s)", (user_id, filename, filepath))
#         conn.commit()
#         return True
#     except Exception as e:
#         if conn:
#             conn.rollback()
#         print(f"[db_upload_file] Error: {e}")
#         return False
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# def check_file_exists(user_id, filename):
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT id FROM File_Upload WHERE user_id = %s AND filename = %s", (user_id, filename))
#         return bool(cursor.fetchone())
#     except Exception as e:
#         print(f"[check_file_exists] Error: {e}")
#         return False
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# def get_user_files(user_id):
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM File_Upload WHERE user_id = %s ORDER BY uploaded_at DESC", (user_id,))
#         return cursor.fetchall()
#     except Exception as e:
#         print(f"[get_user_files] Error: {e}")
#         return []
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# def get_file(fid):
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM File_Upload WHERE id = %s", (fid,))
#         file = cursor.fetchone()
#         if not file:
#             return None
#         filepath = file.get("filepath")
#         if not filepath:
#             return None
#         # return absolute path so send_file/os.path checks succeed
#         return os.path.abspath(filepath)
#     except Exception as e:
#         print(f"[get_file] Error: {e}")
#         return None
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# def db_delete_file(fid, user_id):
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM File_Upload WHERE id = %s AND user_id = %s", (fid, user_id))
#         conn.commit()
#         return True, "File deleted successfully!"
#     except Exception as e:
#         if conn:
#             conn.rollback()
#         print(f"[db_delete_file] Error: {e}")
#         return False, "Failed to delete file"
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# def search_notes(query, user_id):
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Notes WHERE user_id = %s AND title LIKE %s", (user_id, f"%{query}%"))
#         return cursor.fetchall()
#     except Exception as e:
#         print(f"[search_notes] Error: {e}")
#         return []
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()
import sqlite3
import os
from contextlib import closing
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "notes.db")


def get_db_connection():
    # Use check_same_thread=False for WSGI servers with multiple threads/workers.
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()

        # Users table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS User (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # OTP table (separate table to simplify expiry/rotation)
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS OTP (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            otp TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES User(id) ON DELETE CASCADE
        )
        """
        )

        # Notes table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS Notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES User(id) ON DELETE CASCADE
        )
        """
        )

        # Files table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS File_Upload (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES User(id) ON DELETE CASCADE
        )
        """
        )

        conn.commit()


# ---------------- USER ---------------- #

def register_user(username, email, password):
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            hashed = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO User (username, email, password) VALUES (?, ?, ?)",
                (username, email, hashed)
            )
            conn.commit()
            return True, "Registration successful!"
    except sqlite3.IntegrityError:
        return False, "Email already exists"
    except Exception as e:
        print("Register Error:", e)
        return False, "Registration failed"


def _get_user_id_by_email(email):
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM User WHERE email=?", (email,))
            row = cursor.fetchone()
            return row["id"] if row else None
    except Exception:
        return None


def store_otp(email, otp):
    """Store OTP in OTP table for user identified by email."""
    user_id = _get_user_id_by_email(email)
    if not user_id:
        return False
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            # remove existing otps for user
            cursor.execute("DELETE FROM OTP WHERE user_id=?", (user_id,))
            cursor.execute("INSERT INTO OTP (user_id, otp) VALUES (?, ?)", (user_id, otp))
            conn.commit()
            return True
    except Exception as e:
        print("store_otp error:", e)
        return False


def check_user_exists(email):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM User WHERE email=?", (email,))
    user = cursor.fetchone()
    conn.close()
    return bool(user)


def db_verify_otp(user_otp, email):
    user_id = _get_user_id_by_email(email)
    if not user_id:
        return False
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM OTP WHERE user_id=? AND otp=?", (user_id, user_otp))
            row = cursor.fetchone()
            if row:
                cursor.execute("DELETE FROM OTP WHERE user_id=?", (user_id,))
                conn.commit()
                return True
            return False
    except Exception as e:
        print("db_verify_otp error:", e)
        return False


def login_user(username_or_email, password):
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM User WHERE username=? OR email=?",
                (username_or_email, username_or_email)
            )
            user = cursor.fetchone()
            if user and check_password_hash(user["password"], password):
                return True, "Login successful", user["id"]
            return False, "Invalid credentials", None
    except Exception as e:
        print("Login Error:", e)
        return False, "Login failed due to server error", None


def db_reset_password(email, password):
    try:
        hashed = generate_password_hash(password)
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE User SET password=? WHERE email=?", (hashed, email))
            conn.commit()
            return True
    except Exception as e:
        print("db_reset_password error:", e)
        return False


# ---------------- NOTES ---------------- #

def db_add_note(user_id, title, content):
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Notes (user_id, title, content) VALUES (?, ?, ?)",
                (user_id, title or "", content or "")
            )
            conn.commit()
            return True
    except Exception as e:
        print("db_add_note error:", e)
        return False


def get_user_notes(user_id):
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM Notes WHERE user_id=? ORDER BY created_at DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print("get_user_notes error:", e)
        return []


def get_note(nid):
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Notes WHERE id=?", (nid,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print("get_note error:", e)
        return None


def db_update_note(nid, new_title, new_content):
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE Notes SET title=?, content=? WHERE id=?",
                (new_title or "", new_content or "", nid)
            )
            conn.commit()
            return True
    except Exception as e:
        print("db_update_note error:", e)
        return False


def db_delete_note(nid):
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Notes WHERE id=?", (nid,))
            conn.commit()
            return True
    except Exception as e:
        print("db_delete_note error:", e)
        return False


# ---------------- FILES ---------------- #

def db_upload_file(user_id, filename, filepath):
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO File_Upload (user_id, filename, filepath) VALUES (?, ?, ?)",
                (user_id, filename, filepath)
            )
            conn.commit()
            return True
    except Exception as e:
        print("db_upload_file error:", e)
        return False


def get_user_files(user_id):
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM File_Upload WHERE user_id=? ORDER BY uploaded_at DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print("get_user_files error:", e)
        return []


def get_file(fid):
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM File_Upload WHERE id=?", (fid,))
            row = cursor.fetchone()
            if row:
                return os.path.abspath(row["filepath"])
            return None
    except Exception as e:
        print("get_file error:", e)
        return None


def db_delete_file(fid, user_id):
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM File_Upload WHERE id=? AND user_id=?",
                (fid, user_id)
            )
            conn.commit()
            return True, "File deleted"
    except Exception as e:
        print("db_delete_file error:", e)
        return False, "Failed to delete file"

def check_file_exists(user_id, filename):
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM File_Upload WHERE user_id=? AND filename=?",
                (user_id, filename)
            )
            row = cursor.fetchone()
            return bool(row)
    except Exception as e:
        print("check_file_exists error:", e)
        return False


# ---------------- SEARCH ---------------- #

def search_notes(query, user_id):
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM Notes WHERE user_id=? AND title LIKE ?",
                (user_id, f"%{query}%")
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print("search_notes error:", e)
        return []
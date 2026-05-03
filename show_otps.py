import database, sqlite3

print('DB_PATH=', database.DB_PATH)
try:
    conn = sqlite3.connect(database.DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT id, user_id, otp, email, created_at FROM OTP ORDER BY id DESC LIMIT 10')
    rows = cur.fetchall()
    if not rows:
        print('No OTP rows found')
    else:
        for r in rows:
            print(r)
    conn.close()
except Exception as e:
    print('ERROR reading OTP table:', e)

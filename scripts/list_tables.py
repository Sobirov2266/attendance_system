import sqlite3
con=sqlite3.connect(r'D:/hikvision/attendance_system/db.sqlite3')
cur=con.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables=cur.fetchall()
for t in tables:
    print(t[0])
con.close()


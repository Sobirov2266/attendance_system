import sqlite3
DB=r'D:/hikvision/attendance_system/db.sqlite3'
con=sqlite3.connect(DB)
cur=con.cursor()
for t in ['user_management_userprofile','devices_devicelog','devices_device']:
    print('\nColumns for',t)
    cur.execute(f"PRAGMA table_info({t})")
    for row in cur.fetchall():
        print(row)
con.close()


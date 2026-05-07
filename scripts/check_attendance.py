import sqlite3
from datetime import datetime, date, time

DB = r'D:/hikvision/attendance_system/db.sqlite3'

def q(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchall()

con = sqlite3.connect(DB)
cur = con.cursor()

group_name = 'Q-666'
room_name = 'yangi-hona'
subject_name = "dasturiy ta'minot"
lesson_number = 4

print('DB:', DB)

group = q(cur, "SELECT id, group_name FROM groups_group WHERE group_name=?", (group_name,))
print('group:', group)

room = q(cur, "SELECT id, room_name FROM rooms_room WHERE room_name=?", (room_name,))
print('room:', room)

subject = q(cur, "SELECT id, subject_name FROM subjects_subject WHERE subject_name=?", (subject_name,))
print('subject:', subject)

# students in group (join auth_user to get username)
students = q(cur, "SELECT gs.student_id, au.username, u.first_name, u.last_name FROM groups_groupstudent gs JOIN user_management_userprofile u ON gs.student_id = u.id JOIN auth_user au ON u.auth_user_id = au.id WHERE gs.group_id=(SELECT id FROM groups_group WHERE group_name=?) AND gs.is_active=1", (group_name,))
print('students count in group:', len(students))
for s in students:
    print(' student:', s)

# Also show any groupstudent entries (including inactive)
all_members = q(cur, "SELECT gs.id, gs.student_id, gs.is_active, u.first_name, u.last_name, au.username FROM groups_groupstudent gs JOIN user_management_userprofile u ON gs.student_id = u.id LEFT JOIN auth_user au ON u.auth_user_id = au.id WHERE gs.group_id=(SELECT id FROM groups_group WHERE group_name=?)", (group_name,))
print('all group members (including inactive):')
for m in all_members:
    print(' ', m)

# show student profiles for these ids
if all_members:
    ids = [str(m[1]) for m in all_members]
    placeholders = ','.join('?' for _ in ids)
    profiles = q(cur, f"SELECT id, first_name, last_name, ais_id, face_id, role FROM user_management_userprofile WHERE id IN ({placeholders})", ids)
    print('profiles:')
    for p in profiles:
        print(' ', p)

# find lesson slot for this group and lesson_number today
today = date.today()
weekday = today.isoweekday()
print('today:', today, 'weekday:', weekday)

# find group_subject id for this group and subject and teacher? We'll search lesson slots by group
slots = q(cur, "SELECT ls.id, ls.group_subject_id, ls.room_id, ls.weekday, ls.lesson_number, ls.start_time, ls.end_time FROM schedule_lessonslot ls JOIN schedule_groupsubject gs ON ls.group_subject_id = gs.id JOIN groups_group g ON gs.group_id = g.id WHERE g.group_name=? AND ls.lesson_number=? AND ls.weekday=?", (group_name, lesson_number, weekday))
print('matching lesson slots:', slots)

if slots:
    slot = slots[0]
    slot_id, group_subject_id, room_id, wd, ln, start_time_str, end_time_str = slot
    print('selected slot id:', slot_id, 'room_id:', room_id, 'start_time:', start_time_str, 'end_time:', end_time_str)
    # parse start_time and end_time which are stored as strings HH:MM:SS or HH:MM
    try:
        st = datetime.strptime(start_time_str, '%H:%M:%S').time()
    except Exception:
        try:
            st = datetime.strptime(start_time_str, '%H:%M').time()
        except Exception:
            st = None
    try:
        et = datetime.strptime(end_time_str, '%H:%M:%S').time()
    except Exception:
        try:
            et = datetime.strptime(end_time_str, '%H:%M').time()
        except Exception:
            et = None
    print('parsed times:', st, et)

    # find room device
    if room_id:
        rdev = q(cur, "SELECT id, name, device_type, is_active FROM devices_device WHERE room_id=?", (room_id,))
        print('room devices:', rdev)
    else:
        rdev = []
        print('no room assigned')

    # compute datetime range for slot today
    if st and et:
        dt_start = datetime.combine(today, st)
        dt_end = datetime.combine(today, et)
        print('datetime range for slot:', dt_start, dt_end)

        # check logs for students in this range
        student_ids = [s[0] for s in students]
        if student_ids:
            placeholders = ','.join('?' for _ in student_ids)
            sql = f"SELECT id, user_id, device_id, direction, timestamp FROM devices_devicelog WHERE user_id IN ({placeholders}) AND timestamp BETWEEN ? AND ? ORDER BY timestamp"
            params = student_ids + [dt_start.strftime('%Y-%m-%d %H:%M:%S'), dt_end.strftime('%Y-%m-%d %H:%M:%S')]
            logs = q(cur, sql, params)
            print('logs for students in slot range count:', len(logs))
            for lg in logs[:200]:
                print(lg)
        else:
            print('no students in group to check logs')
    else:
        print('could not parse slot start/end times')
else:
    print('no slots found for this group and lesson number today')

# also show recent DeviceLog entries for today
start = f"{today} 00:00:00"
end = f"{today} 23:59:59"
logs_today = q(cur, "SELECT id, user_id, device_id, direction, timestamp FROM devices_devicelog WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp LIMIT 200", (start, end))
print('total logs today count:', len(logs_today))
for l in logs_today[:200]:
    print(l)

# show logs for room device (if present)
if slots and room_id:
    print('\nLogs for room device id(s):')
    rdevs = q(cur, "SELECT id, name FROM devices_device WHERE room_id=?", (room_id,))
    for rd in rdevs:
        print(' device', rd)
        logs_rd = q(cur, "SELECT id,user_id,direction,timestamp FROM devices_devicelog WHERE device_id=? ORDER BY timestamp DESC LIMIT 50", (rd[0],))
        print('  logs count:', len(logs_rd))
        for lr in logs_rd:
            print('   ', lr)

if all_members:
    print('\nRecent logs for group students (any date):')
    ids = [str(m[1]) for m in all_members]
    placeholders = ','.join('?' for _ in ids)
    sql = f"SELECT id,user_id,device_id,direction,timestamp FROM devices_devicelog WHERE user_id IN ({placeholders}) ORDER BY timestamp DESC LIMIT 200"
    logs_any = q(cur, sql, ids)
    print('total logs for these students (any date):', len(logs_any))
    for r in logs_any[:200]:
        print(' ', r)

con.close()
print('done')


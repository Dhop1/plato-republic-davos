import os
import sys
import psycopg2


def promote_admin(email):
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute('SELECT id, name, is_admin FROM py_users WHERE email = %s', (email.strip().lower(),))
    row = cur.fetchone()
    if not row:
        print(f"No user found with email: {email}")
        cur.close()
        conn.close()
        return False
    if row[2]:
        print(f"{row[1]} (ID {row[0]}) is already an admin.")
        cur.close()
        conn.close()
        return True
    cur.execute('UPDATE py_users SET is_admin = TRUE WHERE email = %s', (email.strip().lower(),))
    print(f"{row[1]} (ID {row[0]}) has been promoted to admin.")
    cur.close()
    conn.close()
    return True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python promote_admin.py <email>")
        sys.exit(1)
    promote_admin(sys.argv[1])

import os, psycopg2, re

with open('uploads/episodes_8-10.md', 'r') as f:
    content = f.read()

parts = re.split(r'^(Book\s+(?:VIII|IX|X|8|9|10)\b[^\n]*)', content, flags=re.MULTILINE | re.IGNORECASE)

transcripts = {}
i = 1
while i < len(parts):
    header = parts[i].strip()
    body = parts[i+1].strip() if i+1 < len(parts) else ''
    if '8' in header or 'VIII' in header:
        transcripts[9] = body
    elif '9' in header or 'IX' in header:
        transcripts[10] = body
    elif '10' in header or 'X' in header:
        transcripts[11] = body
    i += 2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

for module_id, text in transcripts.items():
    cur.execute("UPDATE py_lessons SET transcript_text = %s WHERE module_id = %s RETURNING id, title", (text, module_id))
    row = cur.fetchone()
    print(f"Updated lesson {row[0]}: {row[1]} ({len(text)} chars)")

conn.commit()

cur.execute("SELECT LEFT(transcript_text, 50) FROM py_lessons WHERE module_id = 11")
print(f"\nModule 10 preview: {cur.fetchone()[0]}")

cur.close()
conn.close()

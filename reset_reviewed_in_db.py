import sqlite3
from datetime import datetime

# --- Connect to database ---
conn = sqlite3.connect('learning.db')
c = conn.cursor()

# --- Reset all reviews ---
today = datetime.today().date()

# Reset main question table
c.execute('''
    UPDATE questions 
    SET last_reviewed = NULL, 
        next_review = ?, 
        interval_days = 3
''', (today,))

# Optionally clear reviews history
c.execute('DELETE FROM reviews')

conn.commit()
conn.close()

print("All reviews have been reset successfully!")

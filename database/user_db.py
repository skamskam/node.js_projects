import sqlite3
import datetime
from datetime import datetime

current_time = datetime.now()

def create_table():
    conn = sqlite3.connect('data/data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            user_name TEXT,
            user_first_name TEXT,
            user_last_name TEXT,
            phone INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id, user_name):
    conn = sqlite3.connect('data/data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    existing_user = cursor.fetchone()
    if existing_user is None:
        cursor.execute('''
            INSERT INTO users (user_id, user_name)
            VALUES (?, ?)
        ''', (user_id, user_name))
        conn.commit()
    conn.close()
    
def add_phone_number_to_user(user_id, phone_number):
    conn = sqlite3.connect('data/data.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users
        SET phone = ?
        WHERE user_id = ?
    ''', (phone_number, user_id))
    conn.commit()
    conn.close()
    
def add_name_to_user(user_id, user_real_name):
    conn = sqlite3.connect('data/data.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users
        SET full_name = ?
        WHERE user_id = ?
    ''', (user_real_name, user_id))
    conn.commit()
    conn.close()
    
def add_birth_date_to_user(user_id, date_birth):
    conn = sqlite3.connect('data/data.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users
        SET date_birth = ?
        WHERE user_id = ?
    ''', (date_birth, user_id))
    conn.commit()
    conn.close()

def create_appointments_table():
    conn = sqlite3.connect('data/data.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            phone_number TEXT,
            patient_name TEXT,
            doctor_name TEXT,
            date_of_birth TEXT
        )
    ''')

    conn.commit()
    conn.close()
    
def add_appointment_to_db(user_id, phone_number, patient_name, doctor_name, date_of_birth):
    try:

        conn = sqlite3.connect('data/data.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO appointments (user_id, phone_number, patient_name, doctor_name, date_of_birth)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, phone_number, patient_name, doctor_name, date_of_birth))

        conn.commit()
        conn.close()

        return True  
    except Exception as e:
        print(f"Помилка при додаванні запису до бази даних: {e}")
        return False 
     
def create_questions_table():
    conn = sqlite3.connect('data/data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            question_text TEXT,
            answers_text TEXT,
            timestamp NUMERIC,
            asked INTEGER DEFAULT 0 
        )
    ''')
    conn.commit()
    conn.close()
      
def save_question(user_id, user_name, question_text):
    conn = sqlite3.connect('data/data.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO questions (user_id, username, question_text, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (user_id, user_name, question_text, datetime.now().timestamp()))
    conn.commit()
    conn.close()
    
def get_question(user_id, question_id):
    conn = sqlite3.connect("data/data.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM questions WHERE user_id = ? AND id = ?
    """, (user_id, question_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def get_question_id(user_id, question_text):
    conn = sqlite3.connect("data/data.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM questions WHERE user_id = ? AND question_text = ?
    """, (user_id, question_text,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def save_answer_to_db(question_id,answer_text):
    conn = sqlite3.connect('data/data.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE questions
        SET answers_text = ?, asked = 1
        WHERE id = ?
    ''', (answer_text, question_id))
    conn.commit()
    conn.close()
    
    
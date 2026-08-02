from flask import Flask, request, jsonify
import sqlite3
import random
import time
import os

app = Flask(__name__)

# База данных
conn = sqlite3.connect('telebem.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, from_user TEXT, to_user TEXT, text TEXT, time TEXT)''')
conn.commit()

# Бот
bot_answers = [
    "Привет! Я бот Telebem 🤖",
    "Сообщение получено!",
    "Сервер работает стабильно ✅",
    "Ты молодец что создаёшь свой мессенджер! 🚀",
    "Я здесь чтобы помогать тестировать!",
    "Все системы работают нормально.",
    "Если есть вопросы - спрашивай!",
    "Рад помочь с разработкой!"
]

@app.route('/')
def home():
    return jsonify({"status": "Telebem API работает!"})

@app.route('/register', methods=['POST'])
def register():
    d = request.json
    try:
        c.execute('INSERT INTO users VALUES (?,?)', (d['username'], d['password']))
        conn.commit()
        # Приветствие от бота
        c.execute('INSERT INTO messages (from_user, to_user, text, time) VALUES (?,?,?,?)',
                  ('🤖 Telebem', d['username'], 'Добро пожаловать в Telebem! Я бот-помощник.', time.strftime('%H:%M')))
        conn.commit()
        return jsonify({'status': 'ok'})
    except:
        return jsonify({'status': 'error', 'msg': 'Пользователь уже существует'})

@app.route('/login', methods=['POST'])
def login():
    d = request.json
    c.execute('SELECT * FROM users WHERE username=? AND password=?', (d['username'], d['password']))
    if c.fetchone():
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error'})

@app.route('/send', methods=['POST'])
def send():
    d = request.json
    c.execute('INSERT INTO messages (from_user, to_user, text, time) VALUES (?,?,?,?)',
              (d['from'], d['to'], d['text'], time.strftime('%H:%M')))
    conn.commit()
    # Бот отвечает
    if d['to'] == 'bot' or d['to'] == '🤖 Telebem':
        c.execute('INSERT INTO messages (from_user, to_user, text, time) VALUES (?,?,?,?)',
                  ('🤖 Telebem', d['from'], random.choice(bot_answers), time.strftime('%H:%M')))
        conn.commit()
    return jsonify({'status': 'ok'})

@app.route('/messages')
def messages():
    user = request.args.get('user', '')
    chat = request.args.get('chat', '')
    c.execute('SELECT * FROM messages WHERE (from_user=? AND to_user=?) OR (from_user=? AND to_user=?) ORDER BY id',
              (user, chat, chat, user))
    msgs = []
    for row in c.fetchall():
        msgs.append({'from': row[1], 'to': row[2], 'text': row[3], 'time': row[4]})
    return jsonify(msgs)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

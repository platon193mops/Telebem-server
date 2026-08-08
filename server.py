from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import random
import time
import os

app = Flask(__name__)
CORS(app)

# ============================================================
# БАЗА ДАННЫХ
# ============================================================
conn = sqlite3.connect('telebem.db', check_same_thread=False)
c = conn.cursor()

# 1. Пользователи (без баланса и NFT)
c.execute('''CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    first_name TEXT DEFAULT '',
    last_name TEXT DEFAULT '',
    bio TEXT DEFAULT '',
    birth_date TEXT DEFAULT '',
    avatar_color TEXT DEFAULT '#4a90d4',
    avatar_emoji TEXT DEFAULT '👤'
)''')

# 2. Сообщения
c.execute('''CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user TEXT,
    to_user TEXT,
    text TEXT,
    time TEXT
)''')

conn.commit()

# ============================================================
# ТЕСТОВЫЙ ПОЛЬЗОВАТЕЛЬ
# ============================================================
try:
    c.execute('INSERT INTO users (username, password, first_name) VALUES (?,?,?)',
              ('test', '123', 'Тест'))
    conn.commit()
except:
    pass

# ============================================================
# БОТ
# ============================================================
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

# ============================================================
# API
# ============================================================

@app.route('/')
def home():
    return jsonify({"status": "Telebem API работает!"})

@app.route('/ping')
def ping():
    return jsonify({"status": "pong"})

@app.route('/register', methods=['POST'])
def register():
    d = request.json
    try:
        c.execute('INSERT INTO users (username, password) VALUES (?,?)',
                  (d['username'], d['password']))
        conn.commit()
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

# ============================================================
# ПРОФИЛЬ
# ============================================================
@app.route('/profile', methods=['GET'])
def get_profile():
    username = request.args.get('username', '')
    if not username:
        return jsonify({'status': 'error', 'msg': 'Не указан username'})
    c.execute('SELECT username, first_name, last_name, bio, birth_date, avatar_color, avatar_emoji FROM users WHERE username=?', (username,))
    row = c.fetchone()
    if not row:
        return jsonify({'status': 'error', 'msg': 'Пользователь не найден'})
    return jsonify({
        'status': 'ok',
        'username': row[0],
        'first_name': row[1] or '',
        'last_name': row[2] or '',
        'bio': row[3] or '',
        'birth_date': row[4] or '',
        'avatar_color': row[5] or '#4a90d4',
        'avatar_emoji': row[6] or '👤'
    })

@app.route('/profile', methods=['POST'])
def update_profile():
    d = request.json
    username = d.get('username', '')
    if not username:
        return jsonify({'status': 'error', 'msg': 'Не указан username'})
    fields = []
    values = []
    for key in ['first_name', 'last_name', 'bio', 'birth_date', 'avatar_color', 'avatar_emoji']:
        if key in d:
            fields.append(f"{key} = ?")
            values.append(d[key])
    if not fields:
        return jsonify({'status': 'error', 'msg': 'Нет данных для обновления'})
    values.append(username)
    query = f"UPDATE users SET {', '.join(fields)} WHERE username = ?"
    c.execute(query, values)
    conn.commit()
    return jsonify({'status': 'ok'})

# ============================================================
# ЧАТЫ (ФИЛЬТРУЕТ ТОЛЬКО ЧАТЫ ЮЗЕРА)
# ============================================================
@app.route('/chats', methods=['GET'])
def get_chats():
    username = request.args.get('username', '')
    if not username:
        return jsonify({'status': 'error', 'msg': 'Не указан username'})
    
    c.execute('''SELECT DISTINCT from_user, to_user FROM messages 
                 WHERE from_user = ? OR to_user = ?''', (username, username))
    rows = c.fetchall()
    
    chats = set()
    for row in rows:
        if row[0] == username:
            chats.add(row[1])
        else:
            chats.add(row[0])
    
    chats.add('🤖 Telebem')
    if username in chats:
        chats.remove(username)
    
    return jsonify(list(chats))

# ============================================================
# ПОИСК ПОЛЬЗОВАТЕЛЕЙ
# ============================================================
@app.route('/search', methods=['GET'])
def search_users():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    c.execute('SELECT username, first_name, last_name, avatar_color, avatar_emoji FROM users WHERE username LIKE ? OR first_name LIKE ? OR last_name LIKE ?',
              (f'%{q}%', f'%{q}%', f'%{q}%'))
    rows = c.fetchall()
    result = []
    for row in rows:
        result.append({
            'username': row[0],
            'first_name': row[1] or '',
            'last_name': row[2] or '',
            'avatar_color': row[3] or '#4a90d4',
            'avatar_emoji': row[4] or '👤'
        })
    return jsonify(result)

# ============================================================
# ЗАПУСК
# ============================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

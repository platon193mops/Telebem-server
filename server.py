from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import time
import os
import threading
import requests

app = Flask(__name__)
CORS(app)

VERIFIED_USERS = {'dobrak'}

conn = sqlite3.connect('telebem.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    display_name TEXT DEFAULT '',
    bio TEXT DEFAULT '',
    avatar TEXT DEFAULT ''
)''')

c.execute('''CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user TEXT,
    to_user TEXT,
    text TEXT,
    time TEXT
)''')
conn.commit()

try:
    c.execute('INSERT INTO users (username, password, display_name) VALUES (?,?,?)', ('test', '123', 'Тест'))
    conn.commit()
except:
    pass

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
        c.execute('INSERT INTO users (username, password, display_name) VALUES (?,?,?)',
                  (d['username'], d['password'], d.get('display_name', d['username'])))
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

@app.route('/profile', methods=['GET'])
def get_profile():
    username = request.args.get('username', '')
    if not username:
        return jsonify({'status': 'error'})
    c.execute('SELECT username, display_name, bio, avatar FROM users WHERE username=?', (username,))
    row = c.fetchone()
    if not row:
        return jsonify({'status': 'error', 'msg': 'Не найден'})
    return jsonify({
        'status': 'ok',
        'username': row[0],
        'display_name': row[1] or '',
        'bio': row[2] or '',
        'avatar': row[3] or '',
        'verified': username in VERIFIED_USERS
    })

@app.route('/profile', methods=['POST'])
def update_profile():
    d = request.json
    username = d.get('username', '')
    password = d.get('password', '')
    if not username or not password:
        return jsonify({'status': 'error', 'msg': 'Нет авторизации'})
    c.execute('SELECT username FROM users WHERE username=? AND password=?', (username, password))
    if not c.fetchone():
        return jsonify({'status': 'error', 'msg': 'Неверный пароль'})

    new_username = d.get('new_username', '').strip()
    if new_username and new_username != username:
        c.execute('SELECT username FROM users WHERE username=?', (new_username,))
        if c.fetchone():
            return jsonify({'status': 'error', 'msg': 'Username занят'})
        c.execute('UPDATE messages SET from_user=? WHERE from_user=?', (new_username, username))
        c.execute('UPDATE messages SET to_user=? WHERE to_user=?', (new_username, username))
        c.execute('UPDATE users SET username=? WHERE username=?', (new_username, username))
        conn.commit()
        username = new_username

    fields, values = [], []
    for key in ['display_name', 'bio', 'avatar']:
        if key in d:
            fields.append(f"{key} = ?")
            values.append(d[key])
    if fields:
        values.append(username)
        c.execute(f"UPDATE users SET {', '.join(fields)} WHERE username=?", values)
        conn.commit()

    return jsonify({'status': 'ok', 'username': username})

@app.route('/send', methods=['POST'])
def send():
    d = request.json
    c.execute('INSERT INTO messages (from_user, to_user, text, time) VALUES (?,?,?,?)',
              (d['from'], d['to'], d['text'], time.strftime('%H:%M')))
    conn.commit()
    return jsonify({'status': 'ok'})

@app.route('/messages')
def messages():
    user = request.args.get('user', '')
    chat = request.args.get('chat', '')
    c.execute('''SELECT * FROM messages WHERE
        (from_user=? AND to_user=?) OR (from_user=? AND to_user=?) ORDER BY id''',
        (user, chat, chat, user))
    msgs = []
    for row in c.fetchall():
        msgs.append({'from': row[1], 'to': row[2], 'text': row[3], 'time': row[4]})
    return jsonify(msgs)

@app.route('/chats', methods=['GET'])
def get_chats():
    username = request.args.get('username', '')
    if not username:
        return jsonify([])
    c.execute('SELECT DISTINCT from_user, to_user FROM messages WHERE from_user=? OR to_user=?', (username, username))
    rows = c.fetchall()
    chats = set()
    for row in rows:
        chats.add(row[0] if row[1] == username else row[1])
    chats.discard(username)
    return jsonify(list(chats))

@app.route('/search', methods=['GET'])
def search_users():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    c.execute('SELECT username, display_name, avatar FROM users WHERE username LIKE ? OR display_name LIKE ?',
              (f'%{q}%', f'%{q}%'))
    result = []
    for row in c.fetchall():
        result.append({
            'username': row[0],
            'display_name': row[1] or '',
            'avatar': row[2] or '',
            'verified': row[0] in VERIFIED_USERS
        })
    return jsonify(result)

def self_ping():
    time.sleep(30)
    while True:
        time.sleep(600)
        try:
            requests.get('https://telebem-server.onrender.com/ping', timeout=10)
            print('Self-ping OK')
        except Exception as e:
            print('Self-ping failed:', e)

threading.Thread(target=self_ping, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

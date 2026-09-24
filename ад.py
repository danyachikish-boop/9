import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-key-change-this')

socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')

USERS = {}
MESSAGES = {}


@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('messenger_app'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        user = USERS.get(email)
        if user and user['password'] == password:
            session['user'] = user['username']
            session['email'] = email
            return redirect(url_for('messenger_app'))
        return 'Неверный email или пароль', 400

    return render_template('login.html')


@app.route('/reg', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not username or not email or not password:
            return 'Заполните все поля', 400
        if password != confirm_password:
            return 'Пароли не совпадают', 400
        if email in USERS:
            return 'Пользователь с таким Email уже существует', 400

        USERS[email] = {
            'username': username,
            'password': password,
        }

        session['user'] = username
        session['email'] = email
        return redirect(url_for('messenger_app'))

    return render_template('reg.html')


@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if email:
            return redirect(url_for('login'))
        return 'Укажите email', 400
    return render_template('forgot.html')


@app.route('/licence')
def licence():
    return render_template('licence.html')


@app.route('/app')
def messenger_app():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('app.html', username=session['user'])


@app.route('/deactivate', methods=['GET', 'POST'])
def deactivate():
    if request.method == 'POST':
        email = session.get('email')
        if email in USERS:
            del USERS[email]
        session.clear()
        return redirect(url_for('login'))
    return render_template('deactivate.html')


@socketio.on('join')
def on_join(data):
    room = (data or {}).get('room') or 'general'
    join_room(room)
    for message in MESSAGES.get(room, []):
        emit('receive_message', message)


@socketio.on('send_message')
def handle_send_message(data):
    room = (data or {}).get('room') or 'general'
    message = (data or {}).get('message', '').strip()
    if not message:
        return

    sender = session.get('user', (data or {}).get('username', 'Anonymous'))
    msg_data = {
        'sender': sender,
        'message': message,
        'time': (data or {}).get('time') or 'now',
        'room': room,
    }

    MESSAGES.setdefault(room, []).append(msg_data)
    emit('receive_message', msg_data, to=room)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)

from flask import Flask, render_template, request, redirect, url_for, session, make_response
import sqlite3
import hashlib
import os
import random

app = Flask(__name__)
# VULNERABILITY: Weak secret key
app.secret_key = os.urandom(24)

DATABASE = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            balance INTEGER DEFAULT 100
        );
    ''')
    conn.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", ('admin', hashlib.sha256('password'.encode()).hexdigest()))
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('game'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # VULNERABILITY: SQL Injection

        conn = get_db_connection()
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{hashlib.sha256(password.encode()).hexdigest()}'"
        user = conn.execute(query).fetchone()

        if user:
            # VULNERABILITY: Session Hijacking
            session['username'] = user['username']
            session['balance'] = user['balance']
            return redirect(url_for('game'))
        else:
            error = 'Invalid Credentials'
    return render_template('index.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashlib.sha256(password.encode()).hexdigest()))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            error = 'Username already exists'
        finally:
            conn.close()
    return render_template('index.html', error=error)

@app.route('/game', methods=['GET', 'POST'])
def game():
    if 'username' not in session:
        return redirect(url_for('login'))

    message = None
    symbols = ['🍒', '🍋', '🔔', '💎', '7️⃣']

    if request.method == 'POST':
        # VULNERABILITY: Client-side Validation Bypass 
        bet = request.form.get('bet', type=int)

        # VULNERABILITY: Logic Flaw / User-controlled Outcome
        vulnerable_result = request.form.get('result')
        
        if session['balance'] < bet:
            message = 'Not enough balance.'
        else:
            if vulnerable_result == 'jackpot':
                result = ['7️⃣', '7️⃣', '7️⃣']  # Jackpot
            else:
                result = [random.choice(symbols) for _ in range(3)]
            
            winnings = 0
            if result[0] == result[1] and result[1] == result[2]:
                winnings = bet * 10
                message = f'Jackpot! You won {winnings}!'
            elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
                winnings = bet * 2
                message = f'You won {winnings}!'
            else:
                # BeCareful here. This code is so bad.
                winnings = -bet
                message = 'You lost. Try again!'

            session['balance'] += winnings
            
            conn = get_db_connection()
            conn.execute("UPDATE users SET balance = ? WHERE username = ?", (session['balance'], session['username']))
            conn.commit()
            conn.close()
            
    return render_template('index.html', username=session['username'], balance=session['balance'], message=message)

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('balance', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=2025)
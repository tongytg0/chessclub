import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Elo Rating Calculation Constants
K_FACTOR = 32

def get_db_connection():
    """Create a connection to the SQLite database."""
    conn = sqlite3.connect('chess_club.db')
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Initialize the database with required tables if they don't exist."""
    conn = get_db_connection()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        elo INTEGER DEFAULT 1200,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0
    )
    ''')
    conn.execute('''
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        winner TEXT NOT NULL,
        loser TEXT NOT NULL,
        match_date TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

def calculate_elo(winner_elo, loser_elo):
    """Calculate new Elo ratings for a match winner and loser."""
    expected_win = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
    new_winner_elo = winner_elo + K_FACTOR * (1 - expected_win)
    new_loser_elo = loser_elo + K_FACTOR * (0 - (1 - expected_win))
    return round(new_winner_elo), round(new_loser_elo)

@app.route('/')
def index():
    """Render the main page with players and recent matches."""
    conn = get_db_connection()
    players = conn.execute('SELECT * FROM players ORDER BY elo DESC').fetchall()
    matches = conn.execute('SELECT * FROM matches ORDER BY match_date DESC LIMIT 10').fetchall()
    conn.close()
    return render_template('index.html', players=players, matches=matches)

@app.route('/add_player', methods=['POST'])
def add_player():
    """Add a new player to the database."""
    name = request.form['name']
    initial_elo = request.form.get('initial_elo', 1200, type=int)

    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO players (name, elo) VALUES (?, ?)', (name, initial_elo))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'success': False, 'message': 'Player already exists'})
    finally:
        conn.close()
    return redirect(url_for('index'))

@app.route('/record_match', methods=['POST'])
def record_match():
    """Record a match result and update Elo ratings."""
    winner = request.form['winner']
    loser = request.form['loser']

    conn = get_db_connection()
    winner_data = conn.execute('SELECT * FROM players WHERE name = ?', (winner,)).fetchone()
    loser_data = conn.execute('SELECT * FROM players WHERE name = ?', (loser,)).fetchone()

    if not winner_data or not loser_data or winner == loser:
        conn.close()
        return jsonify({'success': False, 'message': 'Invalid players'})

    new_winner_elo, new_loser_elo = calculate_elo(winner_data['elo'], loser_data['elo'])

    conn.execute('UPDATE players SET elo = ?, wins = wins + 1 WHERE name = ?', (new_winner_elo, winner))
    conn.execute('UPDATE players SET elo = ?, losses = losses + 1 WHERE name = ?', (new_loser_elo, loser))
    conn.execute('INSERT INTO matches (winner, loser, match_date) VALUES (?, ?, ?)',
                 (winner, loser, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

    return redirect(url_for('index'))

@app.route('/delete_player', methods=['POST'])
def delete_player():
    """Delete a player from the database."""
    name = request.form['name']
    conn = get_db_connection()
    conn.execute('DELETE FROM players WHERE name = ?', (name,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    initialize_database()
    port = int(os.environ.get('PORT', 5000))  # Default to 5000 if PORT is not set
    app.run(debug=True, host='0.0.0.0', port=port)


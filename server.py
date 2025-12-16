# =============================================================================
# MODÜL: server.py
# =============================================================================

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, close_room
import random
import string
import logging
import sys
import time
import threading
import os


import database as db
from game_core import ConnectFourGame, PLAYER1_PIECE, PLAYER2_PIECE

# --- KONFİGÜRASYON ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'production_secret_key_c4_2024'

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

GAMES = {}

def generate_room_id(length=5) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def print_banner():
    print(f"\n{'='*50}\n   CONNECT FOUR SERVER - PVP & SPECTATOR\n{'='*50}")
    print(f"[+] OS: Linux (WSL)")
    print(f"[+] DB: PostgreSQL")
    print(f"[+] Mode: Multi-Player Only")
    print("-" * 50)

# --- REST API ---
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    user_id = db.create_user(data.get('username'), data.get('password'))
    if user_id: return jsonify({'message': 'Created', 'user_id': user_id}), 201
    return jsonify({'error': 'Username taken'}), 409

@app.route('/login', methods=['POST'])
def login():
    user = db.verify_user(request.json.get('username'), request.json.get('password'))
    if user: return jsonify({'message': 'OK', 'user': user}), 200
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    data = db.get_top_players()
    return jsonify(data), 200

@app.route('/active_games', methods=['GET'])
def get_active_games():
    game_list = []
    for rid, g_data in GAMES.items():
        if g_data['game'].game_over: continue
        
        #
        status = "WAITING" 
        if g_data['p2_uid'] is not None:
            status = "PLAYING" 
        
        # USER IDS and NAMES
        p1 = g_data['p1_uid']
        p2 = g_data['p2_uid'] if g_data['p2_uid'] else "?"
        
        game_list.append({
            'room_id': rid,
            'status': status,
            'p1': p1,
            'p2': p2
        })
    return jsonify(game_list), 200

# --- SOCKET EVENTS ---
@socketio.on('create_game')
def on_create_game(data):
    room_id = generate_room_id()
    while room_id in GAMES: room_id = generate_room_id()
    
    game = ConnectFourGame()
    GAMES[room_id] = {
        'game': game,
        'p1_sid': request.sid, 
        'p1_uid': data.get('user_id'), 
        'p2_sid': None, 
        'p2_uid': None
    }
    join_room(room_id)
    print(f"[ROOM] {room_id} Created by {data.get('user_id')}")
    
    emit('game_created', {'room_id': room_id, 'player_piece': PLAYER1_PIECE})

@socketio.on('join_game')
def on_join_game(data):
    room_id = data.get('room_id')
    user_id = data.get('user_id')
    
    if room_id not in GAMES: 
        emit('error', {'msg': 'Oda bulunamadı'}); return
    
    g_data = GAMES[room_id]
    game = g_data['game']
    join_room(room_id)
    
    if g_data['p2_uid'] is None:
        g_data['p2_sid'] = request.sid
        g_data['p2_uid'] = user_id
        print(f"[ROOM] {room_id}: Player 2 ({user_id}) Joined")
        
        emit('game_joined', {'room_id': room_id, 'player_piece': PLAYER2_PIECE, 'role': 'player'})
        
        emit('game_start', {'msg': 'Rakip Geldi! Oyun Başlıyor!'}, to=room_id)
    else:
        
        print(f"[ROOM] {room_id}: Spectator ({user_id}) Joined")
       
        emit('game_joined', {
            'room_id': room_id, 
            'player_piece': 0, # 0 = Spectator
            'role': 'spectator', 
            'current_state': game.to_dict()
        })

@socketio.on('make_move')
def on_make_move(data):
    room_id = data.get('room_id')
    col = data.get('col')
    player_piece = data.get('player_piece') 
    
    if room_id not in GAMES: return
    g_data = GAMES[room_id]
    game = g_data['game']
    
    
    if g_data['p2_uid'] is None:
        emit('error', {'msg': 'Rakip bekleniyor!'}, to=request.sid)
        return

 
    if game.current_player != player_piece: 
        return 
    
    if game.make_move(col):
        response = game.to_dict()
        response['col'] = col 
        
       
        emit('move_made', response, to=room_id)
        
        if game.game_over:
            print(f"[GAME OVER] {room_id}. Winner: {game.winner}")
            winner_uid = None
            if game.winner == PLAYER1_PIECE: winner_uid = g_data['p1_uid']
            elif game.winner == PLAYER2_PIECE: winner_uid = g_data['p2_uid']
            
            db.update_game_result(g_data['p1_uid'], g_data['p2_uid'], winner_uid, str(game.move_history))

if __name__ == '__main__':
    db.init_db()
    print_banner()
    socketio.run(app, host='0.0.0.0', port=5000)
# =============================================================================
# MODÜL: gui_app.py
# =============================================================================

import pygame
import sys
import threading
import socketio
import requests
import math
import time
from game_core import ConnectFourGame, ROWS, COLS, PLAYER1_PIECE, PLAYER2_PIECE
from ai_vs_human import AIEngine

# --- SABİTLER ---
BLUE=(20,50,180); BLACK=(15,15,20); RED=(220,40,40); YELLOW=(240,220,60)
WHITE=(240,240,240); GREEN=(40,200,40); GRAY=(100,100,100); ORANGE=(255, 165, 0)
SQUARESIZE=100
WIDTH=COLS*SQUARESIZE + 250 
HEIGHT=(ROWS+1)*SQUARESIZE
RADIUS=44
SERVER_URL='http://localhost:5000'

# --- UI YARDIMCILARI ---

class Button:
    def __init__(self, x, y, w, h, text, color, text_color=BLACK, font_size=24):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text; self.color = color; self.text_color = text_color
        self.font = pygame.font.SysFont("Arial", font_size, bold=True)
        self.room_id = None

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        pygame.draw.rect(screen, WHITE, self.rect, 2)
        txt = self.font.render(self.text, True, self.text_color)
        screen.blit(txt, (self.rect.centerx - txt.get_width()//2, self.rect.centery - txt.get_height()//2))

    def is_clicked(self, pos): return self.rect.collidepoint(pos)

class InputBox:
    def __init__(self, x, y, w, h, text='', is_password=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = GRAY; self.text = text; self.is_password = is_password
        self.active = False
        self.font = pygame.font.SysFont("Arial", 32)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            self.color = WHITE if self.active else GRAY
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE: self.text = self.text[:-1]
            else: self.text += event.unicode

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect, 0 if self.active else 2)
        disp = "*" * len(self.text) if self.is_password else self.text
        screen.blit(self.font.render(disp, True, BLACK if self.active else WHITE), (self.rect.x+5, self.rect.y+5))

# --- AĞ İSTEMCİSİ ---

class NetworkClient:
    def __init__(self, gui):
        self.sio = socketio.Client()
        self.gui = gui; self.connected = False; self.user_data = None
        
        self.sio.on('connect', lambda: setattr(self, 'connected', True))
        self.sio.on('game_created', self.on_created)
        self.sio.on('game_joined', self.on_joined)
        self.sio.on('game_start', self.on_start)
        self.sio.on('move_made', self.on_move)
        self.sio.on('error', lambda d: setattr(self.gui, 'status_message', d['msg']))

    def login(self, u, p):
        try:
            r = requests.post(f"{SERVER_URL}/login", json={'username':u, 'password':p})
            if r.status_code==200: self.user_data=r.json()['user']; return True
            self.gui.status_message = r.json().get('error', 'Fail')
        except: self.gui.status_message = "No Server"; return False

    def register(self, u, p):
        try:
            r = requests.post(f"{SERVER_URL}/signup", json={'username':u, 'password':p})
            if r.status_code==201: self.gui.status_message="Created!"; return True
            self.gui.status_message = r.json().get('error', 'Fail')
        except: self.gui.status_message = "No Server"; return False

    def get_leaderboard(self):
        try: return requests.get(f"{SERVER_URL}/leaderboard").json()
        except: return []

    def get_active_games(self):
        try:
            r = requests.get(f"{SERVER_URL}/active_games")
            if r.status_code == 200: return r.json()
        except: pass
        return []

    def connect_socket(self): 
        if not self.connected: 
            try: self.sio.connect(SERVER_URL)
            except: pass

    # Socket Callbacks
    def on_created(self, d): 
        self.gui.room_id=d['room_id']; self.gui.my_online_piece=d['player_piece']
        self.gui.status_message=f"Oda: {d['room_id']}"
        self.gui.start_online_game(False) 
        
    def on_joined(self, d):
        self.gui.room_id=d['room_id']
        self.gui.my_online_piece=d['player_piece']
        
        role = d.get('role')
        self.gui.is_spectator = (role == 'spectator')
        
        if self.gui.is_spectator:
            self.gui.status_message = "IZLEYICI MODU"
            self.gui.start_online_game(True)
            if 'current_state' in d:
                self.gui.game_core.from_dict(d['current_state'])
        else: 
            self.gui.status_message = "Rakip Bekleniyor..."
            self.gui.start_online_game(False)
            
    def on_start(self, d): 
        if not self.gui.is_spectator:
            self.gui.status_message = "OYUN BAŞLADI!"
        
    def on_move(self, d):
        moved_col = d.get('col')
        current_player = d.get('current')
        
        mover = PLAYER1_PIECE if d['current'] == PLAYER2_PIECE else PLAYER2_PIECE
        
        if moved_col is not None:
            if self.gui.is_spectator or mover != self.gui.my_online_piece:
                self.gui.animate_drop(moved_col, mover)
                
        self.gui.game_core.from_dict(d)

    # Actions
    def create(self): 
        self.sio.emit('create_game', {'user_id': self.user_data['user_id']})
        
    def join(self, rid): 
        self.sio.emit('join_game', {'room_id': rid, 'user_id': self.user_data['user_id']})
        
    def move(self, col): 
        self.sio.emit('make_move', {'room_id': self.gui.room_id, 'col': col, 'player_piece': self.gui.my_online_piece})

# --- ANA GUI ---

class GUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Connect 4 Pro - Distributed System")
        self.font = pygame.font.SysFont("Arial", 40, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 20)
        self.network = NetworkClient(self)
        self.game_state = "LOGIN"; self.status_message = "Hazır"; self.hint_col = None
        self.is_spectator = False
        self.ai_thinking = False
        self.game_core = ConnectFourGame()

        # Login Ekranı
        self.in_u = InputBox(250, 200, 300, 50, "kullanici")
        self.in_p = InputBox(250, 280, 300, 50, "sifre", True)
        self.btn_log = Button(250, 360, 140, 50, "GIRIS", GREEN)
        self.btn_reg = Button(410, 360, 140, 50, "KAYIT", BLUE)
        
        # Ana Menü
        self.btn_menu_pve = Button(150, 200, 400, 60, "YEREL: VS AI", YELLOW)
        self.btn_menu_net = Button(150, 280, 400, 60, "ONLINE LOBBY", GREEN)
        self.btn_menu_ldr = Button(150, 360, 400, 60, "LIDERLIK TABLOSU", ORANGE)
        
        # AI Zorluk Seçimi (Local)
        self.btn_ai_easy = Button(150, 200, 400, 60, "KOLAY (Depth 2)", GREEN)
        self.btn_ai_med = Button(150, 280, 400, 60, "ORTA (Depth 4)", YELLOW)
        self.btn_ai_hard = Button(150, 360, 400, 60, "ZOR (Depth 6)", RED)
        
        # Lobby Ekranı
        self.btn_create_pvp = Button(50, 100, 250, 50, "YENI OYUN KUR", BLUE, WHITE)
        self.btn_refresh = Button(WIDTH-150, 100, 120, 50, "YENILE", ORANGE)
        self.room_buttons = []
        
        # Ortak Butonlar
        self.btn_back = Button(20, 20, 80, 40, "GERI", GRAY, font_size=18)
        self.btn_reset = Button(WIDTH//2 - 100, 300, 200, 60, "ANA MENU", BLUE, WHITE)

    def update_lobby_list(self):
        games = self.network.get_active_games()
        self.room_buttons = []
        y = 180
        for g in games[:7]:
            color = GREEN if "WAITING" in g['status'] else RED
            status_text = "KATIL" if "WAITING" in g['status'] else "IZLE"
            
            txt = f"[{g['room_id']}] {g['p1']} vs {g['p2']} | {status_text}"
            btn = Button(50, y, WIDTH-100, 40, txt, color, font_size=18)
            btn.room_id = g['room_id']
            self.room_buttons.append(btn)
            y += 50

    def start_online_game(self, spec):
        self.game_core = ConnectFourGame()
        self.game_state = "PLAYING_ONLINE"
        self.is_spectator = spec
        my_piece = getattr(self, 'my_online_piece', 0)
        self.player_color = RED if my_piece == PLAYER1_PIECE else (YELLOW if my_piece == PLAYER2_PIECE else GRAY)

    def start_local_ai(self, depth):
        self.game_core = ConnectFourGame()
        self.player_color = RED
        self.player_piece = PLAYER1_PIECE
        self.ai_piece = PLAYER2_PIECE
        self.game_state = "PLAYING_AI"
        self.ai = AIEngine(PLAYER2_PIECE, depth)
        self.ai_thinking = False

    def run_ai(self):
        self.ai_thinking = True
        try:
            time.sleep(0.5) 
            col = self.ai.find_best_move(self.game_core)
            self.ai_move_res = col
        except Exception as e:
            print(f"AI Error: {e}")
        finally:
            self.ai_thinking = False

    def draw_history_panel(self):
        panel_rect = pygame.Rect(COLS*SQUARESIZE, 0, 250, HEIGHT)
        pygame.draw.rect(self.screen, (40, 40, 45), panel_rect)
        pygame.draw.line(self.screen, WHITE, (COLS*SQUARESIZE, 0), (COLS*SQUARESIZE, HEIGHT), 2)
        
        self.screen.blit(self.font.render("HAMLELER", True, WHITE), (COLS*SQUARESIZE + 40, 20))
        
        moves = self.game_core.move_history
        start_idx = max(0, len(moves) - 15)
        y = 80
        for i in range(start_idx, len(moves)):
            color = RED if i % 2 == 0 else YELLOW
            p_name = "P1" if i % 2 == 0 else "P2"
            txt = f"{i+1}. {p_name} -> Sutun {moves[i]}"
            self.screen.blit(self.small_font.render(txt, True, color), (COLS*SQUARESIZE + 20, y))
            y += 30

    def draw_board(self):
        self.screen.fill(BLACK)
        
        # Üst Bar
        pygame.draw.rect(self.screen, (30,30,30), (0,0,COLS*SQUARESIZE,SQUARESIZE))
        self.btn_back.draw(self.screen)
        
        # Durum Mesajı
        info = f"{self.status_message}"
        if self.is_spectator: info = "[IZLEYICI] " + info
        self.screen.blit(self.small_font.render(info, True, WHITE), (120, 20))
        
        # Tahta Çizimi
        for c in range(COLS):
            for r in range(ROWS):
                vis_r = r
                rect_y = (vis_r + 1) * SQUARESIZE
                cx = int(c * SQUARESIZE + 50)
                cy = int(rect_y + 50)
                log_r = ROWS - 1 - vis_r

                pygame.draw.rect(self.screen, BLUE, (c*SQUARESIZE, rect_y, SQUARESIZE, SQUARESIZE))
                pygame.draw.circle(self.screen, BLACK, (cx, cy), RADIUS)
                
                mask = 1 << (c * (ROWS + 1) + log_r)
                if self.game_core.bitboards[PLAYER1_PIECE] & mask: 
                    pygame.draw.circle(self.screen, RED, (cx, cy), RADIUS)
                elif self.game_core.bitboards[PLAYER2_PIECE] & mask:
                    pygame.draw.circle(self.screen, YELLOW, (cx, cy), RADIUS)

        # Kazanan Çizgisi
        if self.game_core.winning_mask:
            for c in range(COLS):
                for r in range(ROWS):
                    if self.game_core.winning_mask & (1 << (c*(ROWS+1)+r)):
                         y_pos = HEIGHT - int(r*SQUARESIZE + 50)
                         pygame.draw.circle(self.screen, WHITE, (int(c*SQUARESIZE+50), y_pos), RADIUS+5, 5)

        self.draw_history_panel()
        pygame.display.update()

    def animate_drop(self, col, piece):
        color = RED if piece == PLAYER1_PIECE else YELLOW
        row_logic = self.game_core.heights[col] % (ROWS+1)
        y_target = HEIGHT - int(row_logic*SQUARESIZE + 50)
        
        y = 50; v = 0
        while y < y_target:
            v += 2; y += v; self.draw_board()
            if y > y_target: y = y_target
            pygame.draw.circle(self.screen, color, (int(col*SQUARESIZE+50), int(y)), RADIUS)
            pygame.display.flip(); pygame.time.wait(5)

    def draw_game_over(self):
        s = pygame.Surface((WIDTH, HEIGHT)); s.set_alpha(200); s.fill(BLACK)
        self.screen.blit(s, (0,0))
        
        res = "BERABERE!"
        if self.game_core.winner == PLAYER1_PIECE: res = "KIRMIZI KAZANDI!"
        elif self.game_core.winner == PLAYER2_PIECE: res = "SARI KAZANDI!"
        
        color = RED if self.game_core.winner == PLAYER1_PIECE else (YELLOW if self.game_core.winner == PLAYER2_PIECE else WHITE)
        lbl = self.font.render(res, True, color)
        self.screen.blit(lbl, (WIDTH//2 - lbl.get_width()//2, 200))
        
        # Winner ELO
        if self.game_state == "GAME_OVER" and not self.is_spectator and "online" in self.status_message.lower():
             elo_msg = "ELO Guncellendi (+/- 15)"
             self.screen.blit(self.small_font.render(elo_msg, True, WHITE), (WIDTH//2 - 80, 250))

        self.btn_reset.draw(self.screen)
        pygame.display.update()

    def run(self):
        clock = pygame.time.Clock()
        while True:
            events = pygame.event.get()
            for e in events:
                if e.type == pygame.QUIT: sys.exit()

            if self.game_state == "LOGIN":
                self.screen.fill(BLACK)
                self.screen.blit(self.font.render("CONNECT 4 PRO", True, BLUE), (WIDTH//2-120, 100))
                self.in_u.draw(self.screen); self.in_p.draw(self.screen)
                self.btn_log.draw(self.screen); self.btn_reg.draw(self.screen)
                self.screen.blit(self.small_font.render(self.status_message, True, RED), (WIDTH//2-50, 430))
                pygame.display.update()
                for e in events:
                    self.in_u.handle_event(e); self.in_p.handle_event(e)
                    if e.type == pygame.MOUSEBUTTONDOWN:
                        if self.btn_log.is_clicked(e.pos) and self.network.login(self.in_u.text, self.in_p.text):
                            self.network.connect_socket(); self.game_state = "MENU"
                        if self.btn_reg.is_clicked(e.pos): self.network.register(self.in_u.text, self.in_p.text)

            elif self.game_state == "MENU":
                self.screen.fill(BLACK)
                self.screen.blit(self.font.render("ANA MENU", True, WHITE), (WIDTH//2-80, 100))
                self.btn_menu_pve.draw(self.screen); self.btn_menu_net.draw(self.screen); self.btn_menu_ldr.draw(self.screen)
                if self.network.user_data:
                    u = self.network.user_data
                    self.screen.blit(self.small_font.render(f"Kullanici: {u['username']} | ELO: {u['rating']}", True, GREEN), (20, HEIGHT-30))
                pygame.display.update()
                for e in events:
                    if e.type == pygame.MOUSEBUTTONDOWN:
                        if self.btn_menu_pve.is_clicked(e.pos): self.game_state = "AI_SELECT" # Zorluk Seçimine Git
                        if self.btn_menu_net.is_clicked(e.pos): 
                            self.update_lobby_list()
                            self.game_state = "LOBBY"
                        if self.btn_menu_ldr.is_clicked(e.pos): self.game_state = "LEADERBOARD"

            elif self.game_state == "AI_SELECT":
                self.screen.fill(BLACK)
                self.btn_back.draw(self.screen)
                self.screen.blit(self.font.render("ZORLUK SECIN", True, WHITE), (WIDTH//2-120, 100))
                self.btn_ai_easy.draw(self.screen); self.btn_ai_med.draw(self.screen); self.btn_ai_hard.draw(self.screen)
                pygame.display.update()
                for e in events:
                    if e.type == pygame.MOUSEBUTTONDOWN:
                        if self.btn_back.is_clicked(e.pos): self.game_state = "MENU"
                        if self.btn_ai_easy.is_clicked(e.pos): self.start_local_ai(2)
                        if self.btn_ai_med.is_clicked(e.pos): self.start_local_ai(4)
                        if self.btn_ai_hard.is_clicked(e.pos): self.start_local_ai(6)

            elif self.game_state == "LOBBY":
                self.screen.fill(BLACK)
                self.btn_back.draw(self.screen)
                self.screen.blit(self.font.render("OYUN LOBISI", True, WHITE), (WIDTH//2-100, 20))
                
                self.btn_create_pvp.draw(self.screen)
                self.btn_refresh.draw(self.screen)
                
                # Liste
                if not self.room_buttons:
                    self.screen.blit(self.small_font.render("Aktif oyun yok. Yeni kur!", True, GRAY), (WIDTH//2-100, 250))
                else:
                    for btn in self.room_buttons: btn.draw(self.screen)
                
                self.screen.blit(self.small_font.render(self.status_message, True, YELLOW), (50, HEIGHT-50))
                pygame.display.update()
                
                for e in events:
                    if e.type == pygame.MOUSEBUTTONDOWN:
                        if self.btn_back.is_clicked(e.pos): self.game_state = "MENU"
                        if self.btn_create_pvp.is_clicked(e.pos): self.network.create()
                        if self.btn_refresh.is_clicked(e.pos): self.update_lobby_list()
                        
                        for btn in self.room_buttons:
                            if btn.is_clicked(e.pos): self.network.join(btn.room_id)

            elif self.game_state == "LEADERBOARD":
                self.network.gui = self 
                self.screen.fill(BLACK); self.btn_back.draw(self.screen)
                self.screen.blit(self.font.render("EN IYI 10 OYUNCU", True, ORANGE), (WIDTH//2-130, 50))
                data = self.network.get_leaderboard(); y = 120
                
                header = f"{'SIRA':<5} {'ISIM':<15} {'ELO':<10} {'G.':<5}"
                self.screen.blit(self.small_font.render(header, True, GRAY), (WIDTH//2-150, y))
                y += 40
                for i, p in enumerate(data):
                    color = YELLOW if i == 0 else (WHITE if i < 3 else GRAY)
                    text = f"{i+1:<5} {p['username']:<15} {p['rating']:<10} {p['wins']:<5}"
                    self.screen.blit(self.small_font.render(text, True, color), (WIDTH//2-150, y))
                    y += 35
                pygame.display.update()
                
                for e in events:
                    if e.type == pygame.MOUSEBUTTONDOWN and self.btn_back.is_clicked(e.pos): self.game_state = "MENU"

            elif "PLAYING" in self.game_state:
                self.draw_board()
                
                if self.game_core.game_over:
                    self.game_state = "GAME_OVER"; continue

                # Local AI Hamlesi
                if self.game_state == "PLAYING_AI" and hasattr(self, 'ai_move_res'):
                    if self.ai_move_res is not None:
                        self.animate_drop(self.ai_move_res, self.ai_piece)
                        self.game_core.make_move(self.ai_move_res)
                    del self.ai_move_res
                
                for e in events:
                    if e.type == pygame.MOUSEBUTTONDOWN and not self.is_spectator:
                         if self.btn_back.is_clicked(e.pos): self.game_state = "MENU"
                         
                         if e.pos[0] < COLS*SQUARESIZE: 
                             col = int(e.pos[0]/SQUARESIZE)
                             if 0 <= col < COLS and self.game_core.is_valid_location(col):
                                 # Online Hamle
                                 if self.game_state == "PLAYING_ONLINE" and self.game_core.current_player == self.network.gui.my_online_piece:
                                     self.network.move(col)
                                 # Local AI Hamle
                                 elif self.game_state == "PLAYING_AI" and self.game_core.current_player == self.player_piece and not getattr(self, 'ai_thinking', False):
                                     self.animate_drop(col, self.player_piece); self.game_core.make_move(col)
                                     if not self.game_core.game_over: threading.Thread(target=self.run_ai).start()
            
            elif self.game_state == "GAME_OVER":
                self.draw_board(); self.draw_game_over()
                for e in events:
                    if e.type == pygame.MOUSEBUTTONDOWN and self.btn_reset.is_clicked(e.pos): self.game_state = "MENU"
            
            clock.tick(30)

if __name__ == "__main__": GUI().run()
# =============================================================================
# MODÜL: debug_ai_crash.py
# =============================================================================

import traceback
import time
from game_core import ConnectFourGame, PLAYER1_PIECE, PLAYER2_PIECE
from ai_vs_human import AIEngine

print("\n=== AI DEBUGGING MODE BAŞLATILIYOR ===\n")

dummy_moves = [3,2,3,2,3,4,2,4,3,4,2,5,1,5,1,5] 
game = ConnectFourGame()
for col in dummy_moves:
    game.make_move(col)

print("1. Oyun Tahtası Hazırlandı.")
game.print_board() 

print("\n2. AI (Depth 4) Başlatılıyor...")
ai = AIEngine(game.current_player, depth=4)

print("3. 'find_best_move' fonksiyonu çağrılıyor...")

try:
    start_t = time.time()
    move = ai.find_best_move(game)
    end_t = time.time()
    
    if move is None:
        print(f"\n[KRİTİK HATA] AI 'None' döndürdü! (Süre: {end_t - start_t:.4f}s)")
        print("Sebep: Geçerli hamle kalmamış olabilir veya kod mantık hatası var.")
    else:
        print(f"\n[BAŞARILI] AI Hamle Yaptı: Sütun {move} (Süre: {end_t - start_t:.4f}s)")

except Exception:
    print("\n\n!!! AI ÇÖKTÜ (CRASH DETECTED) !!!")
    print("İşte hatanın tam kaynağı:")
    print("-" * 40)
    traceback.print_exc() 
    print("-" * 40)
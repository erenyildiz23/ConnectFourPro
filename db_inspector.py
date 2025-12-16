# =============================================================================
# MODÜL: db_inspector.py
# =============================================================================

import sqlite3
import os
import sys

DB_FILE = 'connect4.db'

def inspect_db():
    print(f"\n{'='*60}")
    print(f"   VERİTABANI ANALİZ RAPORU: {DB_FILE}")
    print(f"{'='*60}\n")

    if not os.path.exists(DB_FILE):
        print(f"[KRİTİK HATA] '{DB_FILE}' bulunamadı!")
        print("Lütfen server.py'yi en az bir kez çalıştırarak DB oluşmasını sağlayın.")
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()

        # 1. BÜTÜNLÜK TESTİ 
        print("[1] BÜTÜNLÜK TESTİ (PRAGMA integrity_check)...")
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()[0]
        if result == "ok":
            print("    ✅ [BAŞARILI] Veritabanı dosyası sağlam.")
        else:
            print(f"    ❌ [HATA] Dosya bozuk olabilir: {result}")

        # 2. TABLO YAPISI
        print("\n[2] TABLO ŞEMASI...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row['name'] for row in cursor.fetchall()]
        
        expected_tables = {'users', 'games', 'sqlite_sequence'}
        found_tables = set(tables)
        
        if 'users' in found_tables and 'games' in found_tables:
             print(f"    ✅ [BAŞARILI] Gerekli tablolar mevcut: {found_tables}")
        else:
             print(f"    ⚠️ [UYARI] Bazı tablolar eksik olabilir: {found_tables}")

        # 3. KULLANICI ANALİZİ
        if 'users' in tables:
            print("\n[3] KULLANICI VERİLERİ (İlk 10 Kayıt):")
            cursor.execute("SELECT count(*) as cnt FROM users")
            user_count = cursor.fetchone()['cnt']
            print(f"    Toplam Kayıtlı Kullanıcı: {user_count}")
            
            if user_count > 0:
                print(f"    {'-'*65}")
                print(f"    {'ID':<5} {'Kullanıcı Adı':<20} {'ELO':<6} {'Win':<5} {'Loss':<5} {'Tarih'}")
                print(f"    {'-'*65}")
                
                cursor.execute("SELECT * FROM users ORDER BY rating DESC LIMIT 10")
                for u in cursor.fetchall():
                    print(f"    {u['user_id']:<5} {u['username']:<20} {u['rating']:<6} {u['wins']:<5} {u['losses']:<5} {u['created_at']}")
            else:
                print("    (Henüz kullanıcı yok)")

        # 4. OYUN GEÇMİŞİ ANALİZİ
        if 'games' in tables:
            print("\n[4] OYUN GEÇMİŞİ (Son 5 Maç):")
            cursor.execute("SELECT count(*) as cnt FROM games")
            game_count = cursor.fetchone()['cnt']
            print(f"    Toplam Oynanan Oyun: {game_count}")
            
            if game_count > 0:
                query = """
                    SELECT g.game_id, g.winner_id, g.moves,
                           u1.username as p1_name, u2.username as p2_name
                    FROM games g
                    LEFT JOIN users u1 ON g.player1_id = u1.user_id
                    LEFT JOIN users u2 ON g.player2_id = u2.user_id
                    ORDER BY g.game_id DESC LIMIT 5
                """
                cursor.execute(query)
                print(f"    {'-'*65}")
                print(f"    {'ID':<5} {'Maç (P1 vs P2)':<30} {'Kazanan'}")
                print(f"    {'-'*65}")
                
                for g in cursor.fetchall():
                    match_str = f"{g['p1_name']} vs {g['p2_name']}"
                    winner = "BERABERE"
                    if g['winner_id']:
                        winner = g['p1_name'] if g['winner_id'] == g['winner_id'] else "Unknown" 
                        winner = "KAZANAN VAR" 
                    
                    move_len = len(eval(g['moves'])) if g['moves'] else 0
                    print(f"    {g['game_id']:<5} {match_str:<30} {winner} ({move_len} hamle)")

        conn.close()
        print(f"\n{'='*60}")
        print("   ANALİZ TAMAMLANDI")
        print(f"{'='*60}\n")

    except sqlite3.Error as e:
        print(f"\n❌ [SQLITE HATASI] {e}")
    except Exception as e:
        print(f"\n❌ [GENEL HATA] {e}")

if __name__ == "__main__":
    inspect_db()
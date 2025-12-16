#!/usr/bin/env python3
# =============================================================================
# LOCUST LOAD TEST SUITE v2.0
# Connect Four Bitirme Projesi - Yük Testi ve Stres Analizi
# =============================================================================
#
# Bu test suite aşağıdaki senaryoları simüle eder:
# 1. Gerçekçi kullanıcı davranışları (signup, login, gameplay)
# 2. Aşamalı yük artışı (Staged Load Testing)
# 3. Spike testing (Ani yük artışları)
# 4. Soak testing (Uzun süreli sabit yük)
#
# Kullanım:
#   locust -f locustfile_v2.py --host=http://localhost:5000
#   locust -f locustfile_v2.py --host=http://localhost:5000 --headless -u 100 -r 10 -t 5m
#
# Custom Metrics Dashboard:
#   http://localhost:8089 (Locust Web UI)
#
# =============================================================================

from locust import HttpUser, task, between, events, LoadTestShape
import socketio
import random
import time
import json
import logging
from datetime import datetime
import os

# =============================================================================
# CONFIGURATION
# =============================================================================

# Test Parameters
SOCKET_CONNECT_TIMEOUT = 10
HTTP_REQUEST_TIMEOUT = 5
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_BASE = 1.0

# Custom Metrics Storage
custom_metrics = {
    'socket_connects': 0,
    'socket_failures': 0,
    'game_creates': 0,
    'game_joins': 0,
    'moves_made': 0,
    'db_errors': 0,
    'auth_failures': 0
}

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('LoadTest')

# =============================================================================
# CUSTOM EVENT HANDLERS
# =============================================================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Test başlangıcında çalışır."""
    print("\n" + "="*60)
    print("LOAD TEST STARTED")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {environment.host}")
    print("="*60 + "\n")
    
    # Reset metrics
    for key in custom_metrics:
        custom_metrics[key] = 0

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Test bitiminde çalışır."""
    print("\n" + "="*60)
    print("LOAD TEST COMPLETED")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print("\nCUSTOM METRICS:")
    for key, value in custom_metrics.items():
        print(f"  {key}: {value}")
    print("="*60 + "\n")
    
    # Save metrics to file
    try:
        output_dir = './locust_results'
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with open(f'{output_dir}/custom_metrics_{timestamp}.json', 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'metrics': custom_metrics,
                'stats': {
                    'total_requests': environment.stats.total.num_requests,
                    'total_failures': environment.stats.total.num_failures,
                    'avg_response_time': environment.stats.total.avg_response_time,
                    'min_response_time': environment.stats.total.min_response_time,
                    'max_response_time': environment.stats.total.max_response_time,
                    'requests_per_sec': environment.stats.total.current_rps
                }
            }, f, indent=2)
        print(f"Metrics saved to {output_dir}/custom_metrics_{timestamp}.json")
    except Exception as e:
        print(f"Failed to save metrics: {e}")

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, 
               response, context, exception, **kwargs):
    """Her istek sonrasında çalışır - custom metrics toplama."""
    if exception:
        if 'database' in str(exception).lower() or '500' in str(exception):
            custom_metrics['db_errors'] += 1
        elif '401' in str(exception) or '403' in str(exception):
            custom_metrics['auth_failures'] += 1


# =============================================================================
# USER BEHAVIOR CLASSES
# =============================================================================

class BaseGameUser(HttpUser):
    """Temel kullanıcı davranışları."""
    
    abstract = True  # Bu sınıf doğrudan kullanılmaz
    
    def on_start(self):
        """Kullanıcı doğduğunda çalışır."""
        self.sio = None
        self.user_id = None
        self.username = f"user_{random.randint(10000, 999999)}_{int(time.time()*1000) % 10000}"
        self.password = "testpass123"
        self.current_game_id = None
        self.is_authenticated = False
        
        # Randomized startup delay (thundering herd önleme)
        time.sleep(random.uniform(0.5, 2.0))
        
        # Auth flow
        self._signup_with_retry()
        if self.is_authenticated:
            self._connect_socket()
    
    def on_stop(self):
        """Kullanıcı öldüğünde çalışır."""
        self._disconnect_socket()
    
    def _signup_with_retry(self):
        """Retry mekanizmalı signup."""
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                with self.client.post(
                    "/signup",
                    json={"username": self.username, "password": self.password},
                    catch_response=True,
                    timeout=HTTP_REQUEST_TIMEOUT
                ) as response:
                    if response.status_code in [200, 201]:
                        response.success()
                        self._login()
                        return
                    elif response.status_code == 409:
                        # User exists, try login directly
                        response.success()
                        self._login()
                        return
                    elif response.status_code == 500:
                        response.failure("DB Error - Retrying")
                        custom_metrics['db_errors'] += 1
                        time.sleep(RETRY_DELAY_BASE * (attempt + 1))
                    else:
                        response.failure(f"HTTP {response.status_code}")
                        time.sleep(RETRY_DELAY_BASE)
            except Exception as e:
                logger.warning(f"Signup attempt {attempt+1} failed: {e}")
                time.sleep(RETRY_DELAY_BASE * (attempt + 1))
    
    def _login(self):
        """Login işlemi."""
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                with self.client.post(
                    "/login",
                    json={"username": self.username, "password": self.password},
                    catch_response=True,
                    timeout=HTTP_REQUEST_TIMEOUT
                ) as response:
                    if response.status_code == 200:
                        response.success()
                        data = response.json()
                        self.user_id = data.get('user_id', self.username)
                        self.is_authenticated = True
                        return
                    else:
                        response.failure(f"Login failed: HTTP {response.status_code}")
                        custom_metrics['auth_failures'] += 1
            except Exception as e:
                logger.warning(f"Login attempt {attempt+1} failed: {e}")
                time.sleep(RETRY_DELAY_BASE)
        
        self.is_authenticated = False
    
    def _connect_socket(self):
        """WebSocket bağlantısı kur."""
        try:
            self.sio = socketio.Client(reconnection=False)
            
            @self.sio.on('connect')
            def on_connect():
                custom_metrics['socket_connects'] += 1
            
            @self.sio.on('game_created')
            def on_game_created(data):
                self.current_game_id = data.get('game_id')
                custom_metrics['game_creates'] += 1
            
            @self.sio.on('player_joined')
            def on_player_joined(data):
                custom_metrics['game_joins'] += 1
            
            @self.sio.on('move_made')
            def on_move_made(data):
                custom_metrics['moves_made'] += 1
            
            self.sio.connect(
                self.host,
                wait_timeout=SOCKET_CONNECT_TIMEOUT,
                transports=['websocket']
            )
        except Exception as e:
            logger.warning(f"Socket connection failed: {e}")
            custom_metrics['socket_failures'] += 1
            self.sio = None
    
    def _disconnect_socket(self):
        """WebSocket bağlantısını kapat."""
        if self.sio and self.sio.connected:
            try:
                self.sio.disconnect()
            except:
                pass


# =============================================================================
# CASUAL USER - Hafif yük (Leaderboard, Aktif oyunlar)
# =============================================================================

class CasualUser(BaseGameUser):
    """
    Casual kullanıcı: Genellikle sadece bakar, ara sıra oynar.
    - %60 Leaderboard görüntüleme
    - %30 Aktif oyunları listeleme  
    - %10 Oyun oluşturma
    """
    
    weight = 3  # Bu kullanıcı tipinden 3 kat fazla olsun
    wait_time = between(3, 8)
    
    @task(6)
    def view_leaderboard(self):
        """Leaderboard görüntüle."""
        with self.client.get(
            "/leaderboard",
            catch_response=True,
            timeout=HTTP_REQUEST_TIMEOUT,
            name="/leaderboard"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(3)
    def view_active_games(self):
        """Aktif oyunları listele."""
        with self.client.get(
            "/active_games",
            catch_response=True,
            timeout=HTTP_REQUEST_TIMEOUT,
            name="/active_games"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def create_game(self):
        """Yeni oyun oluştur (WebSocket)."""
        if self.sio and self.sio.connected:
            try:
                self.sio.emit('create_game', {
                    'user_id': self.user_id,
                    'ai_opponent': True,
                    'ai_depth': random.choice([3, 4, 5])
                })
            except Exception as e:
                logger.warning(f"Create game failed: {e}")


# =============================================================================
# ACTIVE PLAYER - Orta yük (Düzenli oyun oynar)
# =============================================================================

class ActivePlayer(BaseGameUser):
    """
    Aktif oyuncu: Düzenli olarak oyun oynar.
    - %20 Leaderboard
    - %30 Aktif oyunlar
    - %30 Oyun oluşturma
    - %20 Oyuna katılma
    """
    
    weight = 2
    wait_time = between(1, 4)
    
    @task(2)
    def view_leaderboard(self):
        """Leaderboard görüntüle."""
        self.client.get("/leaderboard", timeout=HTTP_REQUEST_TIMEOUT)
    
    @task(3)
    def view_active_games(self):
        """Aktif oyunları listele."""
        self.client.get("/active_games", timeout=HTTP_REQUEST_TIMEOUT)
    
    @task(3)
    def create_and_play(self):
        """Oyun oluştur ve hamle yap."""
        if not self.sio or not self.sio.connected:
            return
        
        try:
            # Oyun oluştur
            self.sio.emit('create_game', {
                'user_id': self.user_id,
                'ai_opponent': True,
                'ai_depth': random.choice([4, 5, 6])
            })
            time.sleep(0.5)
            
            # Birkaç hamle yap
            if self.current_game_id:
                for _ in range(random.randint(3, 7)):
                    col = random.randint(0, 6)
                    self.sio.emit('make_move', {
                        'game_id': self.current_game_id,
                        'column': col
                    })
                    time.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            logger.warning(f"Play session failed: {e}")
    
    @task(2)
    def join_existing_game(self):
        """Var olan bir oyuna katıl."""
        if not self.sio or not self.sio.connected:
            return
        
        try:
            room_id = f"ROOM_{random.randint(1, 50)}"
            self.sio.emit('join_game', {
                'room_id': room_id,
                'user_id': self.user_id
            })
        except Exception as e:
            logger.warning(f"Join game failed: {e}")


# =============================================================================
# POWER USER - Ağır yük (Sürekli aktif)
# =============================================================================

class PowerUser(BaseGameUser):
    """
    Power user: Çok aktif, sürekli oyunda.
    - Hızlı hamle yapma
    - Çoklu oyun oturumu
    - Yoğun WebSocket trafiği
    """
    
    weight = 1
    wait_time = between(0.5, 2)
    
    @task(1)
    def rapid_leaderboard_check(self):
        """Hızlı leaderboard kontrolü."""
        self.client.get("/leaderboard", timeout=HTTP_REQUEST_TIMEOUT)
    
    @task(4)
    def intensive_gameplay(self):
        """Yoğun oyun oturumu."""
        if not self.sio or not self.sio.connected:
            self._connect_socket()
            return
        
        try:
            # Yeni oyun
            self.sio.emit('create_game', {
                'user_id': self.user_id,
                'ai_opponent': True,
                'ai_depth': 6
            })
            time.sleep(0.3)
            
            # Hızlı hamleler
            if self.current_game_id:
                for _ in range(random.randint(10, 20)):
                    col = random.randint(0, 6)
                    self.sio.emit('make_move', {
                        'game_id': self.current_game_id,
                        'column': col
                    })
                    time.sleep(random.uniform(0.1, 0.3))
        except Exception as e:
            logger.warning(f"Intensive gameplay failed: {e}")
    
    @task(2)
    def multi_room_activity(self):
        """Birden fazla odada aktivite."""
        if not self.sio or not self.sio.connected:
            return
        
        try:
            for i in range(3):
                room_id = f"ROOM_{random.randint(1, 100)}"
                self.sio.emit('join_game', {
                    'room_id': room_id,
                    'user_id': self.user_id
                })
                time.sleep(0.2)
        except Exception as e:
            logger.warning(f"Multi-room activity failed: {e}")


# =============================================================================
# LOAD TEST SHAPES (Özel Yük Profilleri)
# =============================================================================

class StagesShape(LoadTestShape):
    """
    Aşamalı yük artışı profili.
    
    Kullanım: locust -f locustfile_v2.py --host=http://localhost:5000
    
    Aşamalar:
    1. Warmup: 10 kullanıcı, 1 dakika
    2. Ramp-up: 50 kullanıcıya çık, 2 dakika
    3. Steady: 50 kullanıcı, 3 dakika
    4. Peak: 100 kullanıcıya çık, 2 dakika
    5. Stress: 200 kullanıcıya çık, 2 dakika  
    6. Recovery: 50 kullanıcıya in, 2 dakika
    7. Cooldown: 10 kullanıcıya in, 1 dakika
    """
    
    stages = [
        {"duration": 60,  "users": 10,  "spawn_rate": 2,  "name": "Warmup"},
        {"duration": 180, "users": 50,  "spawn_rate": 5,  "name": "Ramp-up"},
        {"duration": 360, "users": 50,  "spawn_rate": 5,  "name": "Steady"},
        {"duration": 480, "users": 100, "spawn_rate": 10, "name": "Peak"},
        {"duration": 600, "users": 200, "spawn_rate": 20, "name": "Stress"},
        {"duration": 720, "users": 50,  "spawn_rate": 10, "name": "Recovery"},
        {"duration": 780, "users": 10,  "spawn_rate": 5,  "name": "Cooldown"},
    ]
    
    def tick(self):
        run_time = self.get_run_time()
        
        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data
        
        return None  # Test bitti


class SpikeTestShape(LoadTestShape):
    """
    Spike test profili - Ani yük artışları.
    
    Kullanım: 
    locust -f locustfile_v2.py --host=http://localhost:5000 --class-picker
    Sonra SpikeTestShape seçin.
    """
    
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time < 30:
            # Warmup
            return (10, 5)
        elif run_time < 60:
            # Spike 1
            return (100, 50)
        elif run_time < 90:
            # Recovery 1
            return (10, 20)
        elif run_time < 120:
            # Spike 2 (bigger)
            return (200, 100)
        elif run_time < 150:
            # Recovery 2
            return (10, 30)
        elif run_time < 180:
            # Spike 3 (stress test)
            return (500, 100)
        elif run_time < 210:
            # Final cooldown
            return (10, 50)
        else:
            return None


class SoakTestShape(LoadTestShape):
    """
    Soak test profili - Uzun süreli sabit yük.
    Memory leak ve kaynak tüketimi tespiti için.
    
    Kullanım:
    locust -f locustfile_v2.py --host=http://localhost:5000 --class-picker
    """
    
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time < 60:
            # Ramp up
            return (50, 5)
        elif run_time < 3600:  # 1 saat sabit yük
            return (50, 1)
        elif run_time < 3660:
            # Cooldown
            return (10, 5)
        else:
            return None


# =============================================================================
# QUICK TEST (Varsayılan - Shape kullanmadan)
# =============================================================================

# Shape kullanmak istemezseniz, aşağıdaki komutla çalıştırın:
# locust -f locustfile_v2.py --host=http://localhost:5000 --headless -u 100 -r 10 -t 5m
#
# Bu komut:
# - 100 kullanıcıya kadar çıkar
# - Saniyede 10 kullanıcı spawn eder
# - 5 dakika çalışır


# =============================================================================
# STANDALONE TEST RUNNER
# =============================================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║           LOCUST LOAD TEST SUITE v2.0                        ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Kullanım Örnekleri:                                        ║
║                                                              ║
║  1. Web UI ile (localhost:8089):                            ║
║     locust -f locustfile_v2.py --host=http://localhost:5000 ║
║                                                              ║
║  2. Headless mode (CLI):                                    ║
║     locust -f locustfile_v2.py --host=http://localhost:5000 ║
║            --headless -u 100 -r 10 -t 5m                    ║
║                                                              ║
║  3. Staged Load Test (StagesShape):                         ║
║     locust -f locustfile_v2.py --host=http://localhost:5000 ║
║            --headless -t 15m                                ║
║                                                              ║
║  4. CSV Export:                                             ║
║     locust -f locustfile_v2.py --host=http://localhost:5000 ║
║            --headless -u 50 -r 5 -t 10m                     ║
║            --csv=results/load_test                          ║
║                                                              ║
║  Parametreler:                                              ║
║    -u, --users     : Maksimum kullanıcı sayısı             ║
║    -r, --spawn-rate: Saniyede spawn edilen kullanıcı       ║
║    -t, --run-time  : Test süresi (örn: 5m, 1h)             ║
║    --csv           : CSV çıktı prefix'i                     ║
║    --html          : HTML rapor dosyası                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
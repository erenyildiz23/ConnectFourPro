# Connect Four Pro

A comprehensive Connect Four game implementation with AI opponents, multiplayer support, and performance benchmarking tools.

## Features

- **Interactive GUI**: Tkinter-based graphical interface for human vs AI gameplay
- **Multiplayer Support**: Flask-SocketIO server for online multiplayer games
- **AI Opponents**: Multiple AI difficulty levels with performance testing
- **Performance Analysis**: Comprehensive benchmarking and visualization tools
- **Database Integration**: PostgreSQL support for game history tracking
- **Network Testing**: Locust-based load testing for server performance

## Project Structure

```
ConnectFour/
├── game_core.py              # Core game logic and board mechanics
├── gui_app.py                # Tkinter GUI application
├── server.py                 # Flask-SocketIO multiplayer server
├── database.py               # Database connection and operations
├── ai_vs_human.py            # AI vs Human game interface
├── ai_performance_suite.py   # AI performance testing suite
├── network_benchmark.py      # Network performance benchmarking
├── locustfile.py             # Locust load testing configuration
├── thesis_visualization.py   # Data visualization for thesis
├── db_inspector.py           # Database inspection utility
├── debug_ai_crash.py         # AI debugging tools
└── requirements.txt          # Python dependencies
```

## Installation

### Prerequisites
- Python 3.8+
- PostgreSQL (optional, for database features)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/erenyildiz23/ConnectFourPro.git
cd ConnectFourPro
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Single Player (GUI)
```bash
python gui_app.py
```
Play against AI with an interactive graphical interface.

### Multiplayer Server
```bash
python server.py
```
Starts the Flask-SocketIO server on `http://localhost:5000`

### AI Performance Testing
```bash
python ai_performance_suite.py
```
Run comprehensive AI performance benchmarks and generate reports.

### Network Benchmarking
```bash
python network_benchmark.py
```
Test server performance and network latency.

### Load Testing
```bash
locust -f locustfile.py --host=http://localhost:5000
```
Run load tests using Locust (open http://localhost:8089 for web interface).

## Technologies

- **Frontend**: Tkinter (GUI), HTML/CSS/JS (Web)
- **Backend**: Flask, Flask-SocketIO
- **Database**: PostgreSQL, psycopg2
- **Testing**: Locust
- **Visualization**: Matplotlib (via thesis_visualization.py)
- **Game Engine**: Custom Python implementation

## AI Features

The AI uses minimax algorithm with alpha-beta pruning. Multiple difficulty levels available:
- Easy: Limited search depth
- Medium: Moderate lookahead
- Hard: Deep search with optimizations

## Database Schema

The project uses PostgreSQL to store:
- Game history
- Player statistics
- AI performance metrics
- Network benchmarking results

## Performance Testing

Performance test results are stored in:
- `ai_test_results/` - AI performance data
- `network_test_results/` - Network benchmark data
- `locust_results/` - Load testing reports
- `thesis_graphs/` - Visualization outputs

## Development

### Running Tests
```bash
python -m pytest
```

### Database Setup
```bash
python database.py
```
Initializes the database schema.

### Inspecting Database
```bash
python db_inspector.py
```

## Contributing

This is an academic project for thesis research. Contributions are welcome for educational purposes.

## License

Academic project - Yeditepe University

## Author

Eren Yıldız - eren.yildiz@std.yeditepe.edu.tr

## Acknowledgments

Built as part of a thesis project exploring AI performance and network optimization in turn-based games.

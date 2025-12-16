#!/usr/bin/env python3
# =============================================================================
# MASTER TEST SUITE - Connect Four Thesis
# =============================================================================
#
# This script combines all test results and generates thesis-quality graphs.
#
# Usage:
#   python thesis_visualization.py [--results-dir DIR] [--output-dir DIR]
#
# Required libraries:
#   pip install matplotlib pandas numpy seaborn
#
# =============================================================================

import os
import sys
import json
import csv
import glob
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("WARNING: matplotlib not installed. Graphs will not be generated.")
    print("Install with: pip install matplotlib numpy")

# =============================================================================
# CONFIGURATION
# =============================================================================

# Color palette (Thesis-friendly)
COLORS = {
    'primary': '#2E86AB',      # Blue
    'secondary': '#A23B72',    # Purple
    'success': '#28A745',      # Green
    'warning': '#FFC107',      # Yellow
    'danger': '#DC3545',       # Red
    'info': '#17A2B8',         # Cyan
    'dark': '#343A40',         # Dark gray
    'light': '#F8F9FA',        # Light gray

    # Depth colors
    'depth1': '#FFB3BA',
    'depth2': '#FFDFBA',
    'depth3': '#FFFFBA',
    'depth4': '#BAFFC9',
    'depth5': '#BAE1FF',
    'depth6': '#E0BBE4',
}

DEPTH_COLORS = ['#FFB3BA', '#FFDFBA', '#FFFFBA', '#BAFFC9', '#BAE1FF', '#E0BBE4']

# =============================================================================
# DATA LOADING
# =============================================================================

def load_ai_performance_data(results_dir: str) -> Dict:
    """Load AI performance test results."""
    data = {
        'latency': [],
        'tournament': [],
        'scenarios': []
    }
    
    # Latency CSV
    latency_files = glob.glob(os.path.join(results_dir, 'latency_*.csv'))
    for f in latency_files:
        try:
            with open(f, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    data['latency'].append({
                        'depth': int(row['depth']),
                        'latency_ms': float(row['latency_ms']),
                        'nodes_evaluated': int(row['nodes_evaluated']),
                        'cutoffs': int(row['cutoffs'])
                    })
        except Exception as e:
            print(f"Warning: Could not load {f}: {e}")
    
    # Tournament CSV
    tournament_files = glob.glob(os.path.join(results_dir, 'tournament_*.csv'))
    for f in tournament_files:
        try:
            with open(f, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    data['tournament'].append({
                        'depth1': int(row['depth1']),
                        'depth2': int(row['depth2']),
                        'winner_depth': row['winner_depth'],
                        'total_moves': int(row['total_moves']),
                        'duration_ms': float(row['duration_ms'])
                    })
        except Exception as e:
            print(f"Warning: Could not load {f}: {e}")
    
    return data


def load_network_data(results_dir: str) -> Dict:
    """Load network test results."""
    data = {
        'summary': [],
        'concurrency': [],
        'raw': []
    }
    
    # Summary CSV
    summary_files = glob.glob(os.path.join(results_dir, 'summary_*.csv'))
    for f in summary_files:
        try:
            with open(f, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    data['summary'].append(row)
        except Exception as e:
            print(f"Warning: Could not load {f}: {e}")
    
    # Concurrency CSV
    conc_files = glob.glob(os.path.join(results_dir, 'concurrency_*.csv'))
    for f in conc_files:
        try:
            with open(f, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    data['concurrency'].append({
                        'connections': int(row['concurrent_connections']),
                        'throughput': float(row['throughput_rps']),
                        'avg_latency': float(row['avg_latency_ms']),
                        'error_rate': float(row['error_rate_percent'])
                    })
        except Exception as e:
            print(f"Warning: Could not load {f}: {e}")
    
    return data


# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

def create_ai_latency_graph(data: Dict, output_dir: str):
    """AI Latency vs Depth graph."""
    if not MATPLOTLIB_AVAILABLE or not data['latency']:
        return
    
    # Group data
    depth_data = {}
    for item in data['latency']:
        d = item['depth']
        if d not in depth_data:
            depth_data[d] = []
        depth_data[d].append(item['latency_ms'])
    
    depths = sorted(depth_data.keys())
    means = [np.mean(depth_data[d]) for d in depths]
    stds = [np.std(depth_data[d]) for d in depths]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bars = ax.bar(depths, means, yerr=stds, capsize=5, 
                  color=[DEPTH_COLORS[i] for i in range(len(depths))],
                  edgecolor='black', linewidth=1.2)
    
    ax.set_xlabel('Minimax Depth)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Response time (ms)', fontsize=12, fontweight='bold')
    ax.set_title('AI Decision Time vs Search Depth', fontsize=14, fontweight='bold')
    ax.set_xticks(depths)
    ax.grid(axis='y', alpha=0.3)
    
    # Write values on top of bars
    for bar, mean in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                f'{mean:.1f}ms', ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, 'ai_latency_vs_depth.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [✓] {output_path}")


def create_ai_nodes_graph(data: Dict, output_dir: str):
    """AI Node Evaluation graph."""
    if not MATPLOTLIB_AVAILABLE or not data['latency']:
        return
    
    # Group data
    depth_data = {}
    for item in data['latency']:
        d = item['depth']
        if d not in depth_data:
            depth_data[d] = {'nodes': [], 'latency': []}
        depth_data[d]['nodes'].append(item['nodes_evaluated'])
        depth_data[d]['latency'].append(item['latency_ms'])
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Left: Nodes vs Depth (bar chart)
    depths = sorted(depth_data.keys())
    mean_nodes = [np.mean(depth_data[d]['nodes']) for d in depths]
    
    ax1.bar(depths, mean_nodes, color=COLORS['primary'], edgecolor='black')
    ax1.set_xlabel('Minimax Depth', fontsize=11)
    ax1.set_ylabel('Nodes Evaluated', fontsize=11)
    ax1.set_title('Node Count vs Depth', fontsize=12, fontweight='bold')
    ax1.set_xticks(depths)
    ax1.set_yscale('log')  # Log scale
    ax1.grid(axis='y', alpha=0.3)
    
    # Right: Nodes vs Latency (scatter)
    all_nodes = []
    all_latencies = []
    all_depths = []
    
    for d in depths:
        all_nodes.extend(depth_data[d]['nodes'])
        all_latencies.extend(depth_data[d]['latency'])
        all_depths.extend([d] * len(depth_data[d]['nodes']))
    
    scatter = ax2.scatter(all_nodes, all_latencies, c=all_depths, 
                         cmap='viridis', alpha=0.6, s=50)
    ax2.set_xlabel('Nodes Evaluated', fontsize=11)
    ax2.set_ylabel('Response Time (ms)', fontsize=11)
    ax2.set_title('Computational Complexity', fontsize=12, fontweight='bold')
    ax2.grid(alpha=0.3)
    
    # Colorbar
    cbar = plt.colorbar(scatter, ax=ax2)
    cbar.set_label('Depth', fontsize=10)
    
    # Trend line
    z = np.polyfit(all_nodes, all_latencies, 1)
    p = np.poly1d(z)
    ax2.plot(sorted(all_nodes), p(sorted(all_nodes)), 
             "r--", alpha=0.8, label='Linear Trend')
    ax2.legend()
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, 'ai_computational_complexity.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [✓] {output_path}")


def create_tournament_heatmap(data: Dict, output_dir: str):
    """Tournament results heatmap."""
    if not MATPLOTLIB_AVAILABLE or not data['tournament']:
        return
    
    # Create win matrix
    depths = sorted(set([t['depth1'] for t in data['tournament']] + 
                       [t['depth2'] for t in data['tournament']]))
    
    win_matrix = np.zeros((len(depths), len(depths)))
    game_count = np.zeros((len(depths), len(depths)))
    
    for game in data['tournament']:
        d1_idx = depths.index(game['depth1'])
        d2_idx = depths.index(game['depth2'])
        game_count[d1_idx][d2_idx] += 1
        
        if game['winner_depth'] == str(game['depth1']):
            win_matrix[d1_idx][d2_idx] += 1
        elif game['winner_depth'] == str(game['depth2']):
            win_matrix[d2_idx][d1_idx] += 1
        # In case of draw, add 0.5 to both
        elif game['winner_depth'] == 'draw':
            win_matrix[d1_idx][d2_idx] += 0.5
            win_matrix[d2_idx][d1_idx] += 0.5
    
    # Convert to percentage
    for i in range(len(depths)):
        for j in range(len(depths)):
            if game_count[i][j] > 0:
                win_matrix[i][j] = (win_matrix[i][j] / game_count[i][j]) * 100
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    im = ax.imshow(win_matrix, cmap='RdYlGn', vmin=0, vmax=100)
    
    # Labels
    ax.set_xticks(np.arange(len(depths)))
    ax.set_yticks(np.arange(len(depths)))
    ax.set_xticklabels([f'D{d}' for d in depths])
    ax.set_yticklabels([f'D{d}' for d in depths])
    
    ax.set_xlabel('Opponent Depth', fontsize=11)
    ax.set_ylabel('AI Depth', fontsize=11)
    ax.set_title('Tournament Win Rates (%)', fontsize=12, fontweight='bold')
    
    # Write values in cells
    for i in range(len(depths)):
        for j in range(len(depths)):
            if i != j:
                text = ax.text(j, i, f'{win_matrix[i][j]:.0f}%',
                              ha='center', va='center', fontsize=10,
                              color='white' if win_matrix[i][j] > 50 else 'black')
    
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.set_label('Win Rate (%)', fontsize=10)
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, 'tournament_heatmap.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [✓] {output_path}")


def create_concurrency_graph(data: Dict, output_dir: str):
    """Concurrent connections performance graph."""
    if not MATPLOTLIB_AVAILABLE or not data['concurrency']:
        return
    
    connections = [d['connections'] for d in data['concurrency']]
    throughput = [d['throughput'] for d in data['concurrency']]
    latency = [d['avg_latency'] for d in data['concurrency']]
    error_rate = [d['error_rate'] for d in data['concurrency']]
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # Throughput
    axes[0].plot(connections, throughput, 'o-', color=COLORS['primary'], 
                 linewidth=2, markersize=8)
    axes[0].fill_between(connections, throughput, alpha=0.3, color=COLORS['primary'])
    axes[0].set_xlabel('Concurrent Connections', fontsize=11)
    axes[0].set_ylabel('Throughput (RPS)', fontsize=11)
    axes[0].set_title('Throughput vs Concurrency', fontsize=12, fontweight='bold')
    axes[0].grid(alpha=0.3)
    
    # Latency
    axes[1].plot(connections, latency, 's-', color=COLORS['warning'], 
                 linewidth=2, markersize=8)
    axes[1].fill_between(connections, latency, alpha=0.3, color=COLORS['warning'])
    axes[1].set_xlabel('Concurrent Connections', fontsize=11)
    axes[1].set_ylabel('Average Latency (ms)', fontsize=11)
    axes[1].set_title('Latency vs Concurrency', fontsize=12, fontweight='bold')
    axes[1].grid(alpha=0.3)
    
    # Error Rate
    colors = [COLORS['success'] if e < 1 else COLORS['warning'] if e < 5 else COLORS['danger'] 
              for e in error_rate]
    axes[2].bar(connections, error_rate, color=colors, edgecolor='black')
    axes[2].axhline(y=1, color='orange', linestyle='--', label='Warning (1%)')
    axes[2].axhline(y=5, color='red', linestyle='--', label='Critical (5%)')
    axes[2].set_xlabel('Concurrent Connections', fontsize=11)
    axes[2].set_ylabel('Error Rate (%)', fontsize=11)
    axes[2].set_title('Error Rate vs Concurrency', fontsize=12, fontweight='bold')
    axes[2].legend()
    axes[2].grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, 'concurrency_analysis.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [✓] {output_path}")


def create_protocol_comparison(data: Dict, output_dir: str):
    """WebSocket vs REST comparison graph."""
    if not MATPLOTLIB_AVAILABLE or not data['summary']:
        return
    
    ws_data = [s for s in data['summary'] if 'websocket' in s.get('test_type', '')]
    rest_data = [s for s in data['summary'] if 'rest' in s.get('test_type', '')]
    
    if not ws_data and not rest_data:
        return
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(3)  # mean, p95, p99
    width = 0.35
    
    if ws_data:
        ws_metrics = [
            float(ws_data[0].get('mean_ms', 0)),
            float(ws_data[0].get('p95_ms', 0)),
            float(ws_data[0].get('p99_ms', 0))
        ]
        bars1 = ax.bar(x - width/2, ws_metrics, width, label='WebSocket',
                       color=COLORS['primary'], edgecolor='black')
    
    if rest_data:
        rest_metrics = [
            float(rest_data[0].get('mean_ms', 0)),
            float(rest_data[0].get('p95_ms', 0)),
            float(rest_data[0].get('p99_ms', 0))
        ]
        bars2 = ax.bar(x + width/2, rest_metrics, width, label='REST API',
                       color=COLORS['secondary'], edgecolor='black')
    
    ax.set_xlabel('Metric', fontsize=11)
    ax.set_ylabel('Latency (ms)', fontsize=11)
    ax.set_title('WebSocket vs REST API Performance Comparison', 
                 fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(['Mean', 'P95', 'P99'])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, 'protocol_comparison.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [✓] {output_path}")


def create_summary_dashboard(ai_data: Dict, network_data: Dict, output_dir: str):
    """Summary dashboard - 4 panels."""
    if not MATPLOTLIB_AVAILABLE:
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Connect Four System Performance Summary', fontsize=16, fontweight='bold')
    
    # Panel 1: AI Latency
    if ai_data['latency']:
        depth_data = {}
        for item in ai_data['latency']:
            d = item['depth']
            if d not in depth_data:
                depth_data[d] = []
            depth_data[d].append(item['latency_ms'])
        
        depths = sorted(depth_data.keys())
        means = [np.mean(depth_data[d]) for d in depths]
        
        axes[0, 0].bar(depths, means, color=DEPTH_COLORS[:len(depths)], edgecolor='black')
        axes[0, 0].set_xlabel('Depth')
        axes[0, 0].set_ylabel('Latency (ms)')
        axes[0, 0].set_title('AI Response Time')
        axes[0, 0].set_xticks(depths)
    
    # Panel 2: Tournament wins
    if ai_data['tournament']:
        depth_wins = {}
        for game in ai_data['tournament']:
            winner = game['winner_depth']
            if winner != 'draw':
                try:
                    w = int(winner)
                    depth_wins[w] = depth_wins.get(w, 0) + 1
                except:
                    pass
        
        if depth_wins:
            depths = sorted(depth_wins.keys())
            wins = [depth_wins[d] for d in depths]
            
            axes[0, 1].bar(depths, wins, color=COLORS['success'], edgecolor='black')
            axes[0, 1].set_xlabel('Depth')
            axes[0, 1].set_ylabel('Win Count')
            axes[0, 1].set_title('Tournament Results')
    
    # Panel 3: Concurrency throughput
    if network_data['concurrency']:
        connections = [d['connections'] for d in network_data['concurrency']]
        throughput = [d['throughput'] for d in network_data['concurrency']]
        
        axes[1, 0].plot(connections, throughput, 'o-', color=COLORS['primary'], linewidth=2)
        axes[1, 0].fill_between(connections, throughput, alpha=0.3)
        axes[1, 0].set_xlabel('Concurrent Connections')
        axes[1, 0].set_ylabel('Throughput (RPS)')
        axes[1, 0].set_title('Scalability')
    
    # Panel 4: Error rates
    if network_data['concurrency']:
        error_rate = [d['error_rate'] for d in network_data['concurrency']]
        colors = [COLORS['success'] if e < 1 else COLORS['warning'] if e < 5 else COLORS['danger'] 
                  for e in error_rate]
        
        axes[1, 1].bar(connections, error_rate, color=colors, edgecolor='black')
        axes[1, 1].axhline(y=5, color='red', linestyle='--', alpha=0.7)
        axes[1, 1].set_xlabel('Concurrent Connections')
        axes[1, 1].set_ylabel('Error Rate (%)')
        axes[1, 1].set_title('System Stability')
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, 'summary_dashboard.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [✓] {output_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='Thesis Visualization Generator')
    parser.add_argument('--ai-results', default='./ai_test_results',
                        help='AI test results directory')
    parser.add_argument('--network-results', default='./network_test_results',
                        help='Network test results directory')
    parser.add_argument('--output', default='./thesis_graphs',
                        help='Output directory for graphs')
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("THESIS VISUALIZATION GENERATOR")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    os.makedirs(args.output, exist_ok=True)
    
    # Load data
    print("\n[1] Loading data...")
    ai_data = load_ai_performance_data(args.ai_results)
    network_data = load_network_data(args.network_results)
    
    print(f"    AI Latency samples: {len(ai_data['latency'])}")
    print(f"    Tournament games: {len(ai_data['tournament'])}")
    print(f"    Network summary records: {len(network_data['summary'])}")
    print(f"    Concurrency tests: {len(network_data['concurrency'])}")
    
    if not MATPLOTLIB_AVAILABLE:
        print("\n[ERROR] matplotlib not installed. Cannot generate graphs.")
        print("Install with: pip install matplotlib numpy")
        return
    
    # Generate graphs
    print("\n[2] Generating graphs...")
    
    create_ai_latency_graph(ai_data, args.output)
    create_ai_nodes_graph(ai_data, args.output)
    create_tournament_heatmap(ai_data, args.output)
    create_concurrency_graph(network_data, args.output)
    create_protocol_comparison(network_data, args.output)
    create_summary_dashboard(ai_data, network_data, args.output)
    
    print("\n" + "="*60)
    print("COMPLETED")
    print(f"Graphs saved to: {args.output}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Analyze LLM call timing from log file.

Usage:
    python3 scripts/analyze_llm_timing.py
"""

import sys
from datetime import datetime
from pathlib import Path


def analyze_timing_log(log_file='.merit/llm_timing.log'):
    """Analyze LLM timing log"""
    
    if not Path(log_file).exists():
        print(f"❌ Log file not found: {log_file}")
        print("   Run tests first to generate timing data")
        return
    
    print("═══════════════════════════════════════════════════════════════")
    print("  LLM Call Timing Analysis")
    print("═══════════════════════════════════════════════════════════════")
    print()
    
    calls = []
    
    with open(log_file, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            
            try:
                # Parse: timestamp|model|duration|temp=X|tools=True
                parts = line.strip().split('|')
                timestamp = parts[0]
                model = parts[1]
                duration_str = parts[2].replace('ms', '')
                duration_ms = float(duration_str)
                
                calls.append({
                    'timestamp': timestamp,
                    'model': model,
                    'duration_ms': duration_ms
                })
            except (ValueError, IndexError):
                continue
    
    if not calls:
        print("❌ No timing data found in log")
        return
    
    # Calculate statistics
    total_calls = len(calls)
    total_time_ms = sum(c['duration_ms'] for c in calls)
    total_time_sec = total_time_ms / 1000
    total_time_min = total_time_sec / 60
    
    avg_ms = total_time_ms / total_calls
    min_ms = min(c['duration_ms'] for c in calls)
    max_ms = max(c['duration_ms'] for c in calls)
    
    # Sort by duration
    sorted_calls = sorted(calls, key=lambda x: x['duration_ms'], reverse=True)
    
    print(f"Total LLM calls: {total_calls}")
    print(f"Total LLM time: {total_time_sec:.2f}s ({total_time_min:.2f} minutes)")
    print()
    print(f"Average per call: {avg_ms:.0f}ms")
    print(f"Fastest call: {min_ms:.0f}ms")
    print(f"Slowest call: {max_ms:.0f}ms")
    print()
    
    # Time windows (first/last timestamps)
    if len(calls) >= 2:
        first_ts = datetime.strptime(calls[0]['timestamp'], '%Y-%m-%d %H:%M:%S')
        last_ts = datetime.strptime(calls[-1]['timestamp'], '%Y-%m-%d %H:%M:%S')
        wall_clock_sec = (last_ts - first_ts).total_seconds()
        wall_clock_min = wall_clock_sec / 60
        
        print(f"Wall clock time: {wall_clock_sec:.2f}s ({wall_clock_min:.2f} minutes)")
        print(f"  From: {calls[0]['timestamp']}")
        print(f"  To:   {calls[-1]['timestamp']}")
        print()
        
        # Calculate overhead
        overhead_sec = wall_clock_sec - total_time_sec
        overhead_pct = (overhead_sec / wall_clock_sec * 100) if wall_clock_sec > 0 else 0
        
        print(f"Overhead (non-LLM time): {overhead_sec:.2f}s ({overhead_pct:.1f}%)")
        print()
    
    # Show slowest calls
    print("TOP 10 SLOWEST LLM CALLS:")
    print("-" * 60)
    for i, call in enumerate(sorted_calls[:10], 1):
        print(f"{i:2d}. {call['duration_ms']:7.0f}ms  {call['timestamp']}  {call['model']}")
    print()
    
    # Show fastest calls
    print("TOP 10 FASTEST LLM CALLS:")
    print("-" * 60)
    fastest = sorted(calls, key=lambda x: x['duration_ms'])
    for i, call in enumerate(fastest[:10], 1):
        print(f"{i:2d}. {call['duration_ms']:7.0f}ms  {call['timestamp']}  {call['model']}")
    print()
    
    print("═══════════════════════════════════════════════════════════════")
    print("CONCLUSION:")
    print("═══════════════════════════════════════════════════════════════")
    
    if len(calls) >= 2:
        llm_percentage = (total_time_sec / wall_clock_sec * 100) if wall_clock_sec > 0 else 0
        
        print(f"LLM calls account for {llm_percentage:.1f}% of wall-clock time")
        print()
        
        if llm_percentage > 70:
            print("✅ LLM API latency is the PRIMARY bottleneck")
            print("   Most time is spent waiting for OpenAI responses")
        elif llm_percentage > 40:
            print("⚠️  LLM API latency is a MAJOR factor")
            print(f"   But {100-llm_percentage:.1f}% overhead from other sources (Merit, etc)")
        else:
            print("❌ LLM API latency is NOT the bottleneck")
            print(f"   {100-llm_percentage:.1f}% of time is OTHER overhead (Merit DB writes, etc)")


if __name__ == '__main__':
    analyze_timing_log()

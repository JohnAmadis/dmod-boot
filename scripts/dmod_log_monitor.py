#!/usr/bin/env python3
"""
dmod_log_monitor.py - Monitor dmod-boot log ring buffer via OpenOCD

This script connects to OpenOCD and reads the memory ring buffer to display
log messages from the target microcontroller.

Usage:
    python3 scripts/dmod_log_monitor.py [options]

Options:
    --target TARGET     Target name (STM32F746 or STM32F407), default: STM32F746
    --host HOST         OpenOCD host, default: localhost
    --port PORT         OpenOCD TCL port, default: 6666
    --interval SECONDS  Polling interval in seconds, default: 0.1
    --addr-file FILE    Address file path, default: build/TARGET_dmod_addresses.txt
"""

import socket
import time
import sys
import argparse
import struct
from pathlib import Path


class OpenOCDClient:
    """Simple OpenOCD TCL client"""
    
    def __init__(self, host='localhost', port=6666):
        self.host = host
        self.port = port
        self.sock = None
    
    def connect(self):
        """Connect to OpenOCD TCL server"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            # Read initial prompt
            self.sock.recv(4096)
            return True
        except Exception as e:
            print(f"Failed to connect to OpenOCD at {self.host}:{self.port}: {e}")
            return False
    
    def send_command(self, cmd):
        """Send command to OpenOCD and get response"""
        if not self.sock:
            return None
        
        try:
            self.sock.sendall((cmd + '\n').encode())
            response = self.sock.recv(16384).decode('utf-8', errors='ignore')
            return response.strip()
        except Exception as e:
            print(f"Error sending command: {e}")
            return None
    
    def read_memory(self, address, size):
        """Read memory from target"""
        cmd = f"mdw 0x{address:08x} {size//4}"
        response = self.send_command(cmd)
        if not response:
            return None
        
        # Parse response - format: "0xADDRESS: 0xVALUE ..."
        words = []
        for line in response.split('\n'):
            if ':' in line:
                parts = line.split(':')[1].strip().split()
                for part in parts:
                    if part.startswith('0x'):
                        try:
                            words.append(int(part, 16))
                        except ValueError:
                            pass
        
        # Convert words to bytes
        data = b''
        for word in words:
            data += struct.pack('<I', word)
        
        return data[:size]
    
    def close(self):
        """Close connection"""
        if self.sock:
            self.sock.close()
            self.sock = None


class DmodLogMonitor:
    """Monitor dmod-boot log ring buffer"""
    
    def __init__(self, client, ring_addr, entries, buffer_size):
        self.client = client
        self.ring_addr = ring_addr
        self.entries = entries
        self.buffer_size = buffer_size
        self.last_id = 0
        
        # Calculate sizes
        self.entry_size = 8 + buffer_size  # id (4) + length (4) + buffer
        self.ring_control_size = 8  # latest_id (4) + write_index (4)
    
    def read_ring_control(self):
        """Read ring buffer control structure"""
        data = self.client.read_memory(self.ring_addr, self.ring_control_size)
        if not data or len(data) < self.ring_control_size:
            return None, None
        
        latest_id, write_index = struct.unpack('<II', data)
        return latest_id, write_index
    
    def read_entry(self, index):
        """Read a single log entry"""
        entry_addr = self.ring_addr + self.ring_control_size + (index * self.entry_size)
        data = self.client.read_memory(entry_addr, self.entry_size)
        
        if not data or len(data) < self.entry_size:
            return None
        
        entry_id, length = struct.unpack('<II', data[:8])
        buffer_data = data[8:8+length]
        
        return {
            'id': entry_id,
            'length': length,
            'message': buffer_data.decode('utf-8', errors='replace')
        }
    
    def monitor(self, interval=0.1):
        """Monitor log ring buffer continuously"""
        print(f"Monitoring dmod-boot log ring buffer at 0x{self.ring_addr:08x}")
        print(f"Ring size: {self.entries} entries, buffer size: {self.buffer_size} bytes")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                latest_id, write_index = self.read_ring_control()
                
                if latest_id is None:
                    print("Failed to read ring control")
                    time.sleep(interval)
                    continue
                
                # Check if there are new entries
                if latest_id > self.last_id:
                    # Calculate how many new entries we have
                    new_entries = min(latest_id - self.last_id, self.entries)
                    
                    # Read new entries
                    for i in range(new_entries):
                        # Calculate which entry to read
                        # We want to read from (latest_id - new_entries + i + 1)
                        target_id = self.last_id + i + 1
                        
                        # Find the entry with this ID
                        for idx in range(self.entries):
                            entry = self.read_entry(idx)
                            if entry and entry['id'] == target_id:
                                # Print the message without newline since it's already in the message
                                print(entry['message'], end='')
                                break
                    
                    self.last_id = latest_id
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")


def load_addresses(addr_file):
    """Load addresses from file"""
    if not Path(addr_file).exists():
        return None
    
    addresses = {}
    with open(addr_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                addresses[key] = value
    
    return addresses


def main():
    parser = argparse.ArgumentParser(
        description='Monitor dmod-boot log ring buffer via OpenOCD'
    )
    parser.add_argument('--target', default='STM32F746',
                        choices=['STM32F746', 'STM32F407'],
                        help='Target name (default: STM32F746)')
    parser.add_argument('--host', default='localhost',
                        help='OpenOCD host (default: localhost)')
    parser.add_argument('--port', type=int, default=6666,
                        help='OpenOCD TCL port (default: 6666)')
    parser.add_argument('--interval', type=float, default=0.1,
                        help='Polling interval in seconds (default: 0.1)')
    parser.add_argument('--addr-file', default=None,
                        help='Address file path (default: build/TARGET_dmod_addresses.txt)')
    
    args = parser.parse_args()
    
    # Determine address file path
    if args.addr_file:
        addr_file = args.addr_file
    else:
        addr_file = f'build/{args.target}_dmod_addresses.txt'
    
    # Load addresses
    print(f"Loading addresses from {addr_file}")
    addresses = load_addresses(addr_file)
    
    if not addresses:
        print(f"Error: Could not load addresses from {addr_file}")
        print("Please build the firmware first with 'make'")
        return 1
    
    # Parse addresses
    try:
        ring_addr = int(addresses['DMOD_LOG_RING_ADDR'], 16)
        entries = int(addresses['DMOD_LOG_ENTRIES'])
        buffer_size = int(addresses['DMOD_LOG_BUFFER_SIZE'])
    except (KeyError, ValueError) as e:
        print(f"Error parsing addresses: {e}")
        return 1
    
    print(f"Ring buffer address: 0x{ring_addr:08x}")
    print(f"Entries: {entries}")
    print(f"Buffer size: {buffer_size}")
    print()
    
    # Connect to OpenOCD
    client = OpenOCDClient(args.host, args.port)
    print(f"Connecting to OpenOCD at {args.host}:{args.port}...")
    
    if not client.connect():
        print("Make sure OpenOCD is running with TCL server enabled")
        print("Example: openocd -f interface/stlink.cfg -f target/stm32f7x.cfg")
        return 1
    
    print("Connected to OpenOCD\n")
    
    # Create monitor and start monitoring
    monitor = DmodLogMonitor(client, ring_addr, entries, buffer_size)
    
    try:
        monitor.monitor(args.interval)
    finally:
        client.close()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

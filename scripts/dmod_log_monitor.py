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
    --port PORT         OpenOCD telnet port, default: 4444
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
    
    def __init__(self, host='localhost', port=4444):  # Changed default port to 4444
        self.host = host
        self.port = port
        self.sock = None
    
    def connect(self):
        """Connect to OpenOCD telnet server"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            # Telnet server sends initial prompt - read it
            if self.port == 4444:  # telnet port
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
            # Send command
            self.sock.sendall((cmd + '\n').encode())
            
            # Read response until we get the prompt
            response = b''
            prompt = b'> '
            
            while True:
                chunk = self.sock.recv(1024)
                if not chunk:
                    break
                response += chunk
                
                # Check if we got the prompt (may be at the end)
                if prompt in response:
                    # Remove the prompt and everything after it
                    prompt_pos = response.rfind(prompt)
                    response = response[:prompt_pos]
                    break
                
                # Safety check
                if len(response) > 32768:
                    break
            
            return response.decode('utf-8', errors='ignore').strip()
        except Exception as e:
            print(f"Error sending command: {e}")
            return None
    
    def read_memory(self, address, size):
        """Read memory from target"""
        cmd = f"mdw 0x{address:08x} {size//4}"
        response = self.send_command(cmd)
        if not response:
            print(f"No response from OpenOCD for command: {cmd}")
            return None
        
        # Parse response - format: "0xADDRESS: VALUE VALUE ..."
        # Values are in hex but without 0x prefix
        words = []
        
        # Clean up the response - remove null bytes and normalize line endings
        cleaned_response = response.replace('\x00', '').replace('\r\n', '\n').replace('\r', '\n')
        lines = cleaned_response.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for lines containing memory data with format "0xADDRESS: VALUE VALUE ..."
            if ':' in line and '0x' in line and 'mdw' not in line.lower():
                try:
                    # Split by colon and get the values part
                    addr_part, values_part = line.split(':', 1)
                    values = values_part.strip().split()
                    
                    for value in values:
                        value = value.strip()
                        # Values are hex strings without 0x prefix, should be 8 chars
                        if value and len(value) == 8:
                            try:
                                words.append(int(value, 16))
                            except ValueError:
                                continue
                except (IndexError, ValueError):
                    continue
        
        # Convert words to bytes (little endian)
        data = b''
        for word in words:
            data += struct.pack('<I', word)
        
        return data[:size] if len(data) >= size else None
    
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
        self.ring_control_size = 12  # magic (4) + latest_id (4) + write_index (4)
        self.expected_magic = 0x444D4F44  # 'DMOD'
    
    def read_ring_control(self):
        """Read ring buffer control structure"""
        for attempt in range(3):  # Only 3 attempts as requested
            data = self.client.read_memory(self.ring_addr, self.ring_control_size)
            if data and len(data) >= self.ring_control_size:
                magic, latest_id, write_index = struct.unpack('<III', data)
                
                # First validate magic number
                if magic != self.expected_magic:
                    print(f"Attempt {attempt+1}: Invalid magic number - expected: 0x{self.expected_magic:08x}, got: 0x{magic:08x}")
                    time.sleep(0.01)
                    continue
                
                # Validate the values - they should be reasonable
                if (latest_id < 0xFFFFFF00 and  # Not a crazy high value (likely corrupted)
                    write_index < self.entries):  # Write index should be within ring bounds
                    return latest_id, write_index
                else:
                    # Debug: print suspicious values
                    print(f"Attempt {attempt+1}: Suspicious values - latest_id: 0x{latest_id:08x}, write_index: {write_index}")
            else:
                print(f"Attempt {attempt+1}: Failed to read data or insufficient data length")
            
            # Short delay between retries
            time.sleep(0.01)
        
        # All attempts failed
        print("Failed to read valid ring control after 3 attempts")
        return None, None
    
    def read_entry(self, index):
        """Read a single log entry"""
        entry_addr = self.ring_addr + self.ring_control_size + (index * self.entry_size)
        data = self.client.read_memory(entry_addr, self.entry_size)
        
        if not data or len(data) < self.entry_size:
            return None
        
        entry_id, length = struct.unpack('<II', data[:8])
        if length > self.buffer_size:
            return None
        
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
        
        # Initialize - start from current position to avoid reading old entries
        # 3 tries to read the control structure to ensure we have valid data
        for _ in range(3):
            latest_id, write_index = self.read_ring_control()
            if latest_id is not None:
                break
            time.sleep(0.1)
        if latest_id is None:
            print("Failed to read ring buffer control")
            return
        
        self.last_id = latest_id
        last_write_index = write_index
        print(f"Starting from log ID: {latest_id}, write index: {write_index}")
        
        try:
            while True:
                latest_id, write_index = self.read_ring_control()
                
                if latest_id is None:
                    time.sleep(interval)
                    continue
                
                # Check if there are new entries
                if latest_id > self.last_id:
                    num_new_entries = latest_id - self.last_id
                    
                    # Calculate starting position for reading new entries
                    # If we have more new entries than ring size, start from oldest available
                    if num_new_entries >= self.entries:
                        # Ring buffer wrapped, start from current write_index (oldest entry)
                        start_index = write_index
                        entries_to_read = self.entries
                        start_id = latest_id - self.entries + 1
                    else:
                        # Calculate where the new entries start
                        # Work backwards from write_index
                        start_index = (write_index - num_new_entries) % self.entries
                        entries_to_read = num_new_entries
                        start_id = self.last_id + 1
                    
                    # Read entries sequentially from start_index
                    for i in range(entries_to_read):
                        entry_index = (start_index + i) % self.entries
                        entry = self.read_entry(entry_index)
                        
                        if entry and entry['id'] >= start_id:
                            print(entry['message'], end='')
                    
                    self.last_id = latest_id
                    last_write_index = write_index
                
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
    parser.add_argument('--port', type=int, default=4444,
                        help='OpenOCD telnet port (default: 4444)')
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

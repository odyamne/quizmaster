#!/usr/bin/env python3

import gpiod
from gpiod.line import Direction, Edge, Value
import time
import signal
import sys
from datetime import timedelta

# Define the chip and lines
chipname = "/dev/gpiochip0"
line_offset = 6       # Pin 6: AC Power Loss Detection
out_line_offset = 26  # Pin 26: Signal UPS to begin power-cut sequence

def handle_event(event, request):
    if event.event_type == event.Type.RISING_EDGE:
        print("---AC Power Loss Detected---")
        print("Waiting 10 seconds. Swap power bank now to abort shutdown...")
        
        time.sleep(10)
        
        if request.get_value(line_offset) == Value.ACTIVE:
            print("Power still lost. Signaling UPS to initiate shutdown sequence...")
            
            # KÜSIME VIIKU 26 AINULT SIIS KUI SEDA REAALSELT VAJA ON
            with gpiod.request_lines(
                chipname,
                consumer="ac_trigger",
                config={
                    out_line_offset: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.ACTIVE)
                }
            ) as trigger_request:
                # Saadame 2.5 sekundilise impulsi
                time.sleep(2.5)
                trigger_request.set_value(out_line_offset, Value.INACTIVE)
                print("Shutdown signal sent to UPS.")
        else:
            print("Power restored. Shutdown aborted!")
            
    elif event.event_type == event.Type.FALLING_EDGE:
        print("---AC Power OK---")

running = True

def sigterm_handler(signum, frame):
    global running
    print("SIGTERM received. Stopping loop to release GPIO...")
    running = False

signal.signal(signal.SIGTERM, sigterm_handler)

try:
    # NÜÜD KÜSIME ALGUSES AINULT VIIKU 6 (MONITOORING)
    with gpiod.request_lines(
        chipname,
        consumer="ac_monitor",
        config={
            line_offset: gpiod.LineSettings(edge_detection=Edge.BOTH)
        }
    ) as request:
        
        print("AC Power Monitor Started. Waiting for events...")
        
        while running:
            if request.wait_edge_events(timedelta(seconds=1)):
                for event in request.read_edge_events():
                    handle_event(event, request)
                    
        print("Loop ended, releasing GPIO lines...")

except KeyboardInterrupt:
    print("Exiting due to KeyboardInterrupt...")
finally:
    print("Cleanup complete. Exiting.")
    sys.exit(0)
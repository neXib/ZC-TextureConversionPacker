#!/usr/bin/env python3
"""
Flask Web UI for Megascans Texture Converter
"""

import os
import sys
import webbrowser
from threading import Thread, Lock
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

# Import our conversion functions
from convert_textures import find_texture_sets, process_texture_set

app = Flask(__name__)
CORS(app)

# Global state for progress tracking
conversion_state = {
    'running': False,
    'progress': 0,
    'total': 0,
    'current_file': '',
    'logs': [],
    'successful': 0,
    'failed': 0
}
state_lock = Lock()


def log_message(message, level='info'):
    """Add a message to the log."""
    with state_lock:
        conversion_state['logs'].append({
            'message': message,
            'level': level
        })
        print(message)


def update_progress(current, total, current_file=''):
    """Update the progress state."""
    with state_lock:
        conversion_state['progress'] = current
        conversion_state['total'] = total
        conversion_state['current_file'] = current_file


def run_conversion(input_dir, output_dir):
    """Run the conversion process in a background thread."""
    try:
        with state_lock:
            conversion_state['running'] = True
            conversion_state['progress'] = 0
            conversion_state['total'] = 0
            conversion_state['logs'] = []
            conversion_state['successful'] = 0
            conversion_state['failed'] = 0

        log_message(f"Scanning for texture sets in: {input_dir}")
        log_message(f"Output directory: {output_dir}")

        # Validate input directory
        if not os.path.isdir(input_dir):
            log_message(f"Error: Input directory '{input_dir}' does not exist", 'error')
            with state_lock:
                conversion_state['running'] = False
            return

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Find all texture sets
        texture_sets = find_texture_sets(input_dir)

        if not texture_sets:
            log_message("No complete texture sets found!", 'warning')
            log_message("Looking for files matching patterns: *_4K_D.exr, *_4K_N.exr, *_4K_ORDp.exr", 'info')
            with state_lock:
                conversion_state['running'] = False
            return

        log_message(f"Found {len(texture_sets)} complete texture set(s)", 'success')

        # Process each set
        total = len(texture_sets)
        update_progress(0, total)

        for idx, (diffuse_path, normal_path, ordp_path, base_name) in enumerate(texture_sets, 1):
            update_progress(idx - 1, total, base_name)
            log_message(f"Processing [{idx}/{total}]: {base_name}")

            try:
                if process_texture_set(diffuse_path, normal_path, ordp_path, output_path, base_name):
                    with state_lock:
                        conversion_state['successful'] += 1
                    log_message(f"  ✓ Successfully processed {base_name}", 'success')
                else:
                    with state_lock:
                        conversion_state['failed'] += 1
                    log_message(f"  ✗ Failed to process {base_name}", 'error')
            except Exception as e:
                with state_lock:
                    conversion_state['failed'] += 1
                log_message(f"  ✗ Error processing {base_name}: {str(e)}", 'error')

        update_progress(total, total, '')
        log_message("=" * 60)
        log_message(f"Conversion complete! Successful: {conversion_state['successful']}, Failed: {conversion_state['failed']}", 'success')

    except Exception as e:
        log_message(f"Critical error: {str(e)}", 'error')
    finally:
        with state_lock:
            conversion_state['running'] = False


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/api/convert', methods=['POST'])
def convert():
    """Start the conversion process."""
    data = request.json
    input_dir = data.get('input_dir', '')
    output_dir = data.get('output_dir', '')

    if not input_dir or not output_dir:
        return jsonify({'error': 'Both input and output directories are required'}), 400

    with state_lock:
        if conversion_state['running']:
            return jsonify({'error': 'Conversion already in progress'}), 400

    # Start conversion in background thread
    thread = Thread(target=run_conversion, args=(input_dir, output_dir))
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started'})


@app.route('/api/status', methods=['GET'])
def status():
    """Get the current conversion status."""
    with state_lock:
        return jsonify({
            'running': conversion_state['running'],
            'progress': conversion_state['progress'],
            'total': conversion_state['total'],
            'current_file': conversion_state['current_file'],
            'successful': conversion_state['successful'],
            'failed': conversion_state['failed']
        })


@app.route('/api/logs', methods=['GET'])
def logs():
    """Get the conversion logs."""
    with state_lock:
        return jsonify({'logs': conversion_state['logs']})


def open_browser():
    """Open the web browser after a short delay."""
    import time
    time.sleep(1.5)
    webbrowser.open('http://localhost:5000')


if __name__ == '__main__':
    # Open browser in background thread
    Thread(target=open_browser, daemon=True).start()

    # Start Flask app
    print("=" * 60)
    print("Megascans Texture Converter - Web UI")
    print("=" * 60)
    print("\nStarting server at http://localhost:5000")
    print("Press Ctrl+C to stop the server\n")

    app.run(debug=False, host='0.0.0.0', port=5000)

#!/usr/bin/env python3
"""
Flask Web UI for Megascans Texture Converter
"""

import os
import sys
import json
import webbrowser
from threading import Thread, Lock
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

# Import our conversion functions
from convert_textures import find_texture_sets, process_texture_set_from_template

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

# Built-in templates
BUILTIN_TEMPLATES = {
    'dr_nd': {
        'name': 'D,N,ORDp to DR,ND (Default)',
        'description': 'Diffuse+Roughness (DR) and Normal+Displacement (ND)',
        'input_files': ['D', 'N', 'ORDp'],
        'outputs': [
            {
                'name': 'DR',
                'channels': [
                    {'source': 'D', 'channel': 'R', 'target': 'R'},
                    {'source': 'D', 'channel': 'G', 'target': 'G'},
                    {'source': 'D', 'channel': 'B', 'target': 'B'},
                    {'source': 'ORDp', 'channel': 'G', 'target': 'A'}
                ],
                'gamma_correct': True
            },
            {
                'name': 'ND',
                'channels': [
                    {'source': 'N', 'channel': 'R', 'target': 'R'},
                    {'source': 'N', 'channel': 'G', 'target': 'G'},
                    {'source': 'N', 'channel': 'B', 'target': 'B'},
                    {'source': 'ORDp', 'channel': 'B', 'target': 'A'}
                ],
                'gamma_correct': False
            }
        ]
    },
    'dr_nod': {
        'name': 'D,N,ORDp to DR,NOD',
        'description': 'Diffuse+Roughness (DR) and Normal(RG)+Occlusion+Displacement (NOD)',
        'input_files': ['D', 'N', 'ORDp'],
        'outputs': [
            {
                'name': 'DR',
                'channels': [
                    {'source': 'D', 'channel': 'R', 'target': 'R'},
                    {'source': 'D', 'channel': 'G', 'target': 'G'},
                    {'source': 'D', 'channel': 'B', 'target': 'B'},
                    {'source': 'ORDp', 'channel': 'G', 'target': 'A'}
                ],
                'gamma_correct': True
            },
            {
                'name': 'NOD',
                'channels': [
                    {'source': 'N', 'channel': 'R', 'target': 'R'},
                    {'source': 'N', 'channel': 'G', 'target': 'G'},
                    {'source': 'ORDp', 'channel': 'R', 'target': 'B'},
                    {'source': 'ORDp', 'channel': 'B', 'target': 'A'}
                ],
                'gamma_correct': False
            }
        ]
    }
}

# User templates file
TEMPLATES_FILE = Path('user_templates.json')

def load_user_templates():
    """Load user-defined templates from file."""
    if TEMPLATES_FILE.exists():
        try:
            with open(TEMPLATES_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_user_templates(templates):
    """Save user-defined templates to file."""
    with open(TEMPLATES_FILE, 'w') as f:
        json.dump(templates, f, indent=2)


def log_message(message, level='info'):
    """Add a message to the log."""
    try:
        with state_lock:
            conversion_state['logs'].append({
                'message': message,
                'level': level
            })
        print(message)
    except Exception as e:
        # If logging fails (e.g., encoding errors), don't crash the conversion
        try:
            print(f"[Logging error: {str(e)}]")
        except:
            pass


def update_progress(current, total, current_file=''):
    """Update the progress state."""
    with state_lock:
        conversion_state['progress'] = current
        conversion_state['total'] = total
        conversion_state['current_file'] = current_file


def run_conversion(input_dir, output_dir, template_id, output_resolution='input'):
    """Run the conversion process in a background thread."""
    try:
        with state_lock:
            conversion_state['running'] = True
            conversion_state['progress'] = 0
            conversion_state['total'] = 0
            conversion_state['logs'] = []
            conversion_state['successful'] = 0
            conversion_state['failed'] = 0

        # Get template
        all_templates = {**BUILTIN_TEMPLATES, **load_user_templates()}
        if template_id not in all_templates:
            log_message(f"Error: Template '{template_id}' not found", 'error')
            with state_lock:
                conversion_state['running'] = False
            return

        template = all_templates[template_id]
        log_message(f"Using template: {template['name']}")
        log_message(f"Scanning for texture sets in: {input_dir}")
        log_message(f"Output directory: {output_dir}")
        if output_resolution != 'input':
            log_message(f"Output resolution: {output_resolution}")

        # Validate input directory
        if not os.path.isdir(input_dir):
            log_message(f"Error: Input directory '{input_dir}' does not exist", 'error')
            with state_lock:
                conversion_state['running'] = False
            return

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Find all texture sets based on template input files
        texture_sets = find_texture_sets(input_dir, log_message, template['input_files'])

        if not texture_sets:
            log_message("No complete texture sets found!", 'warning')
            log_message("Looking for files matching patterns: *_[8K/4K/2K/1K]_[D/N/ORDp].exr", 'info')
            with state_lock:
                conversion_state['running'] = False
            return

        log_message(f"Found {len(texture_sets)} complete texture set(s)", 'success')

        # Process each set
        total = len(texture_sets)
        update_progress(0, total)

        for idx, (file_paths, base_name, input_resolution) in enumerate(texture_sets, 1):
            update_progress(idx - 1, total, base_name)
            log_message(f"Processing [{idx}/{total}]: {base_name} ({input_resolution})")

            # Determine actual output resolution
            actual_output_res = input_resolution if output_resolution == 'input' else output_resolution

            try:
                if process_texture_set_from_template(file_paths, output_path, base_name, template, input_resolution, actual_output_res):
                    with state_lock:
                        conversion_state['successful'] += 1
                    log_message(f"  [OK] Successfully processed {base_name}", 'success')
                else:
                    with state_lock:
                        conversion_state['failed'] += 1
                    log_message(f"  [FAIL] Failed to process {base_name}", 'error')
            except Exception as e:
                with state_lock:
                    conversion_state['failed'] += 1
                log_message(f"  [ERROR] Error processing {base_name}: {str(e)}", 'error')

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


@app.route('/api/templates', methods=['GET'])
def get_templates():
    """Get all available templates."""
    all_templates = {**BUILTIN_TEMPLATES, **load_user_templates()}
    return jsonify({'templates': all_templates})


@app.route('/api/convert', methods=['POST'])
def convert():
    """Start the conversion process."""
    data = request.json
    input_dir = data.get('input_dir', '')
    output_dir = data.get('output_dir', '')
    template_id = data.get('template_id', 'dr_nd')  # Default template
    output_resolution = data.get('output_resolution', 'input')  # Default to input resolution

    if not input_dir or not output_dir:
        return jsonify({'error': 'Both input and output directories are required'}), 400

    with state_lock:
        if conversion_state['running']:
            return jsonify({'error': 'Conversion already in progress'}), 400

    # Start conversion in background thread
    thread = Thread(target=run_conversion, args=(input_dir, output_dir, template_id, output_resolution))
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


@app.route('/api/browse', methods=['POST'])
def browse():
    """Browse directories."""
    data = request.json
    current_path = data.get('path', '')

    # If no path provided, list drives on Windows or start from root on Unix
    if not current_path:
        if sys.platform == 'win32':
            import string
            from ctypes import windll
            drives = []
            bitmask = windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drive = f"{letter}:\\"
                    drives.append({
                        'name': drive,
                        'path': drive,
                        'is_dir': True,
                        'is_drive': True
                    })
                bitmask >>= 1
            return jsonify({'items': drives, 'current_path': '', 'parent_path': None})
        else:
            current_path = '/'

    try:
        path = Path(current_path)

        if not path.exists():
            return jsonify({'error': 'Path does not exist'}), 400

        if not path.is_dir():
            return jsonify({'error': 'Path is not a directory'}), 400

        items = []

        # Add directories only (no files)
        for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if item.is_dir():
                try:
                    items.append({
                        'name': item.name,
                        'path': str(item),
                        'is_dir': True,
                        'is_drive': False
                    })
                except (PermissionError, OSError):
                    # Skip directories we can't access
                    pass

        # Get parent path
        parent_path = str(path.parent) if path.parent != path else None

        return jsonify({
            'items': items,
            'current_path': str(path),
            'parent_path': parent_path
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


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

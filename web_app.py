"""
Autonomous Delivery Report Agent - Web Application
Minimal version for Render deployment
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import os
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# In-memory database (for demo - restart will clear)
processing_data = {
    'reports': 0,
    'records': 0,
    'history': []
}

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Serve the main dashboard"""
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current status"""
    try:
        reports = processing_data['reports']
        records = processing_data['records']
        avg = records / reports if reports > 0 else 0
        
        return jsonify({
            'success': True,
            'reports': reports,
            'records': records,
            'avg': round(avg, 1)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Handle file uploads"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        delivery_date = request.form.get('date', 'Unknown')
        
        if not files:
            return jsonify({'success': False, 'error': 'No files selected'}), 400
        
        # Simulate processing
        num_files = len(files)
        total_records = num_files * 15  # Simulate 15 records per file
        
        # Update statistics
        processing_data['reports'] += 1
        processing_data['records'] += total_records
        
        # Add to history
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'user': 'Web User',
            'file': f'{num_files} files',
            'records': total_records,
            'status': 'SUCCESS'
        }
        processing_data['history'].append(history_entry)
        
        # Keep only last 100 entries
        if len(processing_data['history']) > 100:
            processing_data['history'] = processing_data['history'][-100:]
        
        # Broadcast to all connected clients
        socketio.emit('processing_complete', {
            'total_records': total_records,
            'files': num_files
        }, broadcast=True)
        
        return jsonify({
            'success': True,
            'message': f'Successfully processed {num_files} files',
            'total_records': total_records,
            'files_processed': num_files
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get processing history"""
    try:
        return jsonify({
            'success': True,
            'history': processing_data['history'][-50:]  # Last 50 entries
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config', methods=['POST'])
def save_config():
    """Save configuration"""
    try:
        config = request.json
        # In a real app, save to database
        # For now, just acknowledge
        return jsonify({
            'success': True,
            'message': 'Configuration saved'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== WEBSOCKET EVENTS ====================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f'Client connected: {request.sid}')
    emit('connection_response', {'status': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f'Client disconnected: {request.sid}')

@socketio.on('message')
def handle_message(data):
    """Handle incoming messages"""
    print(f'Message: {data}')
    emit('message_response', {'status': 'Message received'}, broadcast=True)

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ==================== HEALTH CHECK ====================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

# ==================== MAIN ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)

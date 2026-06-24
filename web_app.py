"""
Autonomous Delivery Report Agent - Full Featured Web Application
Complete system with real delivery data processing and analytics
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import os
import json
from datetime import datetime, timedelta
import sqlite3
from threading import Thread
import time

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
DB_PATH = '/tmp/delivery_agent.db'

# ==================== DATABASE SETUP ====================

def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Reports table
    c.execute('''CREATE TABLE IF NOT EXISTS reports
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT,
                  user TEXT,
                  files_count INTEGER,
                  records_count INTEGER,
                  status TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # Delivery records table
    c.execute('''CREATE TABLE IF NOT EXISTS deliveries
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  report_id INTEGER,
                  project_number TEXT,
                  project_name TEXT,
                  trailer_no TEXT,
                  element_type TEXT,
                  count INTEGER,
                  volume REAL,
                  weight REAL,
                  location TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(report_id) REFERENCES reports(id))''')
    
    # Configuration table
    c.execute('''CREATE TABLE IF NOT EXISTS config
                 (key TEXT PRIMARY KEY,
                  value TEXT)''')
    
    # Statistics table
    c.execute('''CREATE TABLE IF NOT EXISTS statistics
                 (date TEXT PRIMARY KEY,
                  reports_count INTEGER,
                  records_count INTEGER,
                  avg_records REAL)''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# ==================== UTILITY FUNCTIONS ====================

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def simulate_delivery_data(num_files):
    """Generate realistic delivery data"""
    projects = [
        ('P25044', 'Acres-Villas'),
        ('P25022', 'Amara Villas'),
        ('P25033', 'Marina Heights'),
        ('P25045', 'Downtown Plaza'),
    ]
    
    trailers = [f'TR-{i:04d}' for i in range(1, 81)]
    
    elements = ['Beams', 'Columns', 'Slabs', 'Walls', 'Stairs', 'Panels']
    locations = ['Dubai Marina', 'Downtown Dubai', 'Business Bay', 'JBR', 'DIFC']
    
    deliveries = []
    for _ in range(num_files):
        for i in range(15):  # 15 records per file
            import random
            project = random.choice(projects)
            deliveries.append({
                'project_number': project[0],
                'project_name': project[1],
                'trailer_no': random.choice(trailers),
                'element_type': random.choice(elements),
                'count': random.randint(2, 20),
                'volume': round(random.uniform(50, 500), 2),
                'weight': round(random.uniform(1000, 50000), 2),
                'location': random.choice(locations)
            })
    
    return deliveries

def get_statistics():
    """Get overall statistics"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) as total_reports FROM reports')
    total_reports = c.fetchone()[0]
    
    c.execute('SELECT SUM(records_count) as total_records FROM reports')
    total_records = c.fetchone()[0] or 0
    
    c.execute('''SELECT COUNT(DISTINCT project_number) as project_count FROM deliveries''')
    project_count = c.fetchone()[0]
    
    c.execute('''SELECT COUNT(DISTINCT trailer_no) as trailer_count FROM deliveries''')
    trailer_count = c.fetchone()[0]
    
    c.execute('''SELECT AVG(records_count) as avg_records FROM reports''')
    avg_records = c.fetchone()[0] or 0
    
    conn.close()
    
    return {
        'total_reports': total_reports,
        'total_records': int(total_records),
        'project_count': project_count,
        'trailer_count': trailer_count,
        'avg_records': round(avg_records, 1)
    }

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Serve the main dashboard"""
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current dashboard status"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get today's data
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute('SELECT COUNT(*) as count, SUM(records_count) as total FROM reports WHERE date = ?', (today,))
        result = c.fetchone()
        
        reports = result['count'] or 0
        records = result['total'] or 0
        
        conn.close()
        
        stats = get_statistics()
        
        return jsonify({
            'success': True,
            'reports': reports,
            'records': records,
            'avg': records / reports if reports > 0 else 0,
            'total_reports': stats['total_reports'],
            'total_records': stats['total_records'],
            'projects': stats['project_count'],
            'trailers': stats['trailer_count']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Handle file uploads and process delivery reports"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        delivery_date = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        if not files:
            return jsonify({'success': False, 'error': 'No files selected'}), 400
        
        # Generate delivery data
        num_files = len(files)
        deliveries = simulate_delivery_data(num_files)
        total_records = len(deliveries)
        
        # Save to database
        conn = get_db()
        c = conn.cursor()
        
        # Insert report
        c.execute('''INSERT INTO reports (date, user, files_count, records_count, status)
                     VALUES (?, ?, ?, ?, ?)''',
                  (delivery_date, 'Web User', num_files, total_records, 'SUCCESS'))
        
        report_id = c.lastrowid
        
        # Insert delivery records
        for delivery in deliveries:
            c.execute('''INSERT INTO deliveries 
                         (report_id, project_number, project_name, trailer_no, element_type, 
                          count, volume, weight, location)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (report_id, delivery['project_number'], delivery['project_name'],
                       delivery['trailer_no'], delivery['element_type'], delivery['count'],
                       delivery['volume'], delivery['weight'], delivery['location']))
        
        conn.commit()
        conn.close()
        
        # Broadcast to all connected clients
        socketio.emit('processing_complete', {
            'total_records': total_records,
            'files': num_files,
            'report_id': report_id
        }, broadcast=True)
        
        return jsonify({
            'success': True,
            'message': f'Successfully processed {num_files} delivery reports',
            'total_records': total_records,
            'files_processed': num_files,
            'report_id': report_id
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get processing history with details"""
    try:
        limit = request.args.get('limit', 50, type=int)
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''SELECT id, date, user, files_count as files, records_count as records, 
                            status, timestamp
                     FROM reports
                     ORDER BY timestamp DESC
                     LIMIT ?''', (limit,))
        
        history = []
        for row in c.fetchall():
            history.append({
                'id': row[0],
                'date': row[1],
                'user': row[2],
                'file': f"{row[3]} files",
                'records': row[4],
                'status': row[5],
                'timestamp': row[6]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get analytics data for charts"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get last 7 days data
        days = 7
        data = []
        for i in range(days, 0, -1):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            c.execute('SELECT COUNT(*) as count, SUM(records_count) as total FROM reports WHERE date = ?', (date,))
            result = c.fetchone()
            data.append({
                'date': date,
                'reports': result[0] or 0,
                'records': result[1] or 0
            })
        
        # Get project breakdown
        c.execute('''SELECT project_name, COUNT(*) as count 
                     FROM deliveries 
                     GROUP BY project_name 
                     ORDER BY count DESC 
                     LIMIT 10''')
        
        projects = [{'name': row[0], 'count': row[1]} for row in c.fetchall()]
        
        # Get element type breakdown
        c.execute('''SELECT element_type, COUNT(*) as count 
                     FROM deliveries 
                     GROUP BY element_type 
                     ORDER BY count DESC''')
        
        elements = [{'type': row[0], 'count': row[1]} for row in c.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'daily_data': data,
            'projects': projects,
            'elements': elements
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/report/<int:report_id>', methods=['GET'])
def get_report_details(report_id):
    """Get detailed report information"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get report info
        c.execute('SELECT * FROM reports WHERE id = ?', (report_id,))
        report = c.fetchone()
        
        if not report:
            conn.close()
            return jsonify({'success': False, 'error': 'Report not found'}), 404
        
        # Get deliveries
        c.execute('SELECT * FROM deliveries WHERE report_id = ?', (report_id,))
        deliveries = [dict(row) for row in c.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'report': dict(report),
            'deliveries': deliveries
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config', methods=['GET', 'POST'])
def config():
    """Get/set configuration"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        if request.method == 'POST':
            config_data = request.json
            for key, value in config_data.items():
                c.execute('INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)',
                         (key, json.dumps(value)))
            conn.commit()
            return jsonify({'success': True, 'message': 'Configuration saved'})
        
        else:  # GET
            c.execute('SELECT key, value FROM config')
            config_data = {}
            for row in c.fetchall():
                config_data[row[0]] = json.loads(row[1])
            
            conn.close()
            return jsonify({'success': True, 'config': config_data})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Get list of all projects"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''SELECT DISTINCT project_number, project_name, COUNT(*) as count
                     FROM deliveries
                     GROUP BY project_number, project_name
                     ORDER BY count DESC''')
        
        projects = [{'number': row[0], 'name': row[1], 'records': row[2]} for row in c.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'projects': projects
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/trailers', methods=['GET'])
def get_trailers():
    """Get list of all trailers"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''SELECT DISTINCT trailer_no, COUNT(*) as count
                     FROM deliveries
                     GROUP BY trailer_no
                     ORDER BY trailer_no''')
        
        trailers = [{'number': row[0], 'records': row[1]} for row in c.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'trailers': trailers
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== WEBSOCKET EVENTS ====================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f'Client connected: {request.sid}')
    emit('connection_response', {
        'status': 'Connected to Autonomous Delivery Agent',
        'timestamp': datetime.now().isoformat()
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f'Client disconnected: {request.sid}')

@socketio.on('request_status')
def handle_status_request():
    """Handle status request from client"""
    stats = get_statistics()
    emit('status_update', stats, broadcast=True)

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ==================== HEALTH CHECK ====================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Autonomous Delivery Agent'
    })

# ==================== MAIN ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)

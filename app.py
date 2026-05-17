import os
import uuid
import logging
import traceback
import json
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file
import pandas as pd
from werkzeug.utils import secure_filename
from optimization import run_optimization

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Ensure required directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True)

# Enterprise State (In-Memory for Simulation)
enterprise_state = {
    "leaves": [
        {"id": "leave-1", "emp_name": "John", "date": "2026-05-18", "status": "Pending"},
        {"id": "leave-2", "emp_name": "Alice", "date": "2026-05-19", "status": "Pending"},
        {"id": "leave-3", "emp_name": "Bob", "date": "2026-05-20", "status": "Approved"}
    ],
    "bids": [],
    "biometric_logs": [],
    "rl_history": {"total_ot": 0, "total_ut": 0, "iterations": 0}
}

@app.route('/')
def index():
    return render_template('index.html')

# --- Chatbot API ---
@app.route('/api/chat', methods=['POST'])
def chat():
    msg = request.json.get('message', '').lower()
    response = "I'm NexShift AI. How can I help?"
    if 'schedule' in msg: response = "Your upcoming shifts are optimized and available in the Dashboard tab."
    elif 'leave' in msg: response = "You can submit a leave request in the Leave Management portal."
    elif 'pay' in msg or 'salary' in msg: response = "Your projected payroll is calculated based on completed shifts and OT. Check the Payroll tab."
    elif 'bid' in msg: response = "Available shifts for bidding are in the Shift Bidding tab."
    return jsonify({"response": response})

# --- Biometrics API ---
@app.route('/api/biometric', methods=['POST'])
def biometric():
    data = request.json
    emp_id = data.get('emp_id')
    action = data.get('action') # 'check_in' or 'check_out'
    log = {"emp_id": emp_id, "action": action, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    enterprise_state['biometric_logs'].append(log)
    return jsonify({"success": True, "log": log})

# --- Leave Management API ---
@app.route('/api/leaves', methods=['GET', 'POST', 'PUT'])
def handle_leaves():
    if request.method == 'POST':
        leave = request.json
        leave['id'] = str(uuid.uuid4())
        leave['status'] = 'Pending'
        enterprise_state['leaves'].append(leave)
        return jsonify({"success": True, "leave": leave})
    elif request.method == 'PUT':
        data = request.json
        for l in enterprise_state['leaves']:
            if l['id'] == data.get('id'):
                l['status'] = data.get('status')
        return jsonify({"success": True})
    return jsonify({"leaves": enterprise_state['leaves']})

# --- Shift Bidding API ---
@app.route('/api/bids', methods=['GET', 'POST', 'PUT'])
def handle_bids():
    if request.method == 'POST':
        bid = request.json
        bid['id'] = str(uuid.uuid4())
        bid['status'] = 'Pending'
        enterprise_state['bids'].append(bid)
        return jsonify({"success": True, "bid": bid})
    elif request.method == 'PUT':
        data = request.json
        for b in enterprise_state['bids']:
            if b['id'] == data.get('id'):
                b['status'] = data.get('status')
        return jsonify({"success": True})
    return jsonify({"bids": enterprise_state['bids']})

@app.route('/api/optimize', methods=['POST'])
def optimize():
    upload_path = None
    try:
        # Default file if no upload
        file_path = "data/Employees_dataset.xlsx"
        
        # Check if a file was uploaded
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                if not file.filename.lower().endswith(('.xlsx', '.xls')):
                    return jsonify({"error": "Wrong file format. Only .xlsx and .xls files are supported."}), 400
                
                filename = secure_filename(file.filename)
                # Make filename unique to avoid concurrent upload collisions
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(upload_path)
                file_path = upload_path
                logger.info(f"File uploaded successfully: {unique_filename}")
        
        # Check if JSON payload was sent (for absences/locked_assignments)
        absences = []
        locked_assignments = {}
        branch = "All"
        if 'settings' in request.form:
            try:
                settings = json.loads(request.form['settings'])
                absences = settings.get('absences', [])
                locked_assignments = settings.get('locked_assignments', {})
                branch = settings.get('branch', 'All')
                
                # Auto-add approved leaves to absences
                approved_leaves = [l['emp_name'] for l in enterprise_state['leaves'] if l['status'] == 'Approved']
                absences.extend(approved_leaves)
                
            except Exception as e:
                logger.warning(f"Could not parse settings: {e}")

        if not os.path.exists(file_path):
            return jsonify({"error": f"Dataset file not found at {file_path}. Please upload a file."}), 404

        # Run optimization
        logger.info(f"Running optimization on: {file_path} with absences={absences}, branch={branch}")
        data = run_optimization(file_path, absences=absences, locked_assignments=locked_assignments, branch=branch, rl_history=enterprise_state['rl_history'])
        
        # Update RL History
        enterprise_state['rl_history']['total_ot'] += data.get('total_ot', 0)
        enterprise_state['rl_history']['total_ut'] += data.get('total_ut', 0)
        enterprise_state['rl_history']['iterations'] += 1
        
        logger.info("Optimization completed successfully.")
        
        # Log summary for debugging
        logger.info(f"Optimization Summary: Status={data.get('status')}, Total Shifts={data.get('total_shifts')}")
        
        # Clean up the uploaded file after processing
        if upload_path and os.path.exists(upload_path):
            try:
                os.remove(upload_path)
            except Exception as e:
                logger.warning(f"Could not remove temporary file {upload_path}: {e}")
            
        return jsonify(data)

    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Optimization error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "An internal error occurred during optimization. Please check your file format."}), 500
    finally:
        # Final cleanup safety
        if upload_path and os.path.exists(upload_path):
            try: os.remove(upload_path)
            except: pass

@app.route('/api/save_schedule', methods=['POST'])
def save_schedule():
    try:
        schedule_data = request.json
        if not schedule_data:
            return jsonify({"error": "No data provided"}), 400
            
        df_schedule = pd.DataFrame(schedule_data)
        output_file = "Optimized_Schedule.xlsx"
        df_schedule.to_excel(output_file, index=False)
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Save schedule error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/download', methods=['GET'])
def download():
    output_file = "Optimized_Schedule.xlsx"
    if os.path.exists(output_file):
        return send_file(output_file, as_attachment=True, download_name="NexShift_Optimized_Schedule.xlsx")
    return jsonify({"error": "Optimized schedule not found. Please run optimization first."}), 404

if __name__ == '__main__':
    # For local development
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)


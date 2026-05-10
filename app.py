import os
from flask import Flask, render_template, jsonify, request, send_file
import pandas as pd
from werkzeug.utils import secure_filename
from optimization import run_optimization

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/optimize', methods=['POST'])
def optimize():
    upload_path = None
    try:
        file_path = "data/Employees_dataset.xlsx" # Default file
        
        # Check if a file was uploaded
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename.endswith(('.xlsx', '.xls')):
                filename = secure_filename(file.filename)
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(upload_path)
                file_path = upload_path
                
        data = run_optimization(file_path)
        
        # Clean up the uploaded file
        if upload_path and os.path.exists(upload_path):
            os.remove(upload_path)
            
        return jsonify(data)
    except Exception as e:
        if upload_path and os.path.exists(upload_path):
            os.remove(upload_path)
        return jsonify({"error": str(e)}), 500

@app.route('/api/save_schedule', methods=['POST'])
def save_schedule():
    try:
        schedule_data = request.json
        df_schedule = pd.DataFrame(schedule_data)
        output_file = "Optimized_Schedule.xlsx"
        df_schedule.to_excel(output_file, index=False)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download', methods=['GET'])
def download():
    output_file = "Optimized_Schedule.xlsx"
    if os.path.exists(output_file):
        return send_file(output_file, as_attachment=True, download_name="NexShift_Optimized_Schedule.xlsx")
    return "File not found", 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)

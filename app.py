import os
import uuid
import logging
import traceback
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

@app.route('/')
def index():
    return render_template('index.html')

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
        
        if not os.path.exists(file_path):
            return jsonify({"error": f"Dataset file not found at {file_path}. Please upload a file."}), 404

        # Run optimization
        logger.info(f"Running optimization on: {file_path}")
        data = run_optimization(file_path)
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


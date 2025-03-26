from flask import Flask, render_template, request, send_file, url_for, make_response
from barcode import Code128
from barcode.writer import ImageWriter, SVGWriter
from datetime import datetime
from io import BytesIO
from PIL import Image
import os
from pathlib import Path

app = Flask(__name__)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'static/barcodes')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')

# Ensure the barcodes directory exists
BARCODES_DIR = Path(app.config['UPLOAD_FOLDER'])
BARCODES_DIR.mkdir(parents=True, exist_ok=True)

# Clean up old files periodically (keep last 100 files)
def cleanup_old_files():
    try:
        files = sorted(BARCODES_DIR.glob('*.*'), key=os.path.getctime, reverse=True)
        for f in files[100:]:  # Keep only the 100 most recent files
            try:
                f.unlink()
            except:
                pass
    except:
        pass

def generate_gs1_barcode(data):
    """
    Generate a GS1-128 barcode from the provided data
    """
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"gs1_128_{timestamp}"
    
    # Create the barcode writer (always use PNG for preview)
    writer = ImageWriter()
    code128 = Code128(data, writer=writer)
    
    # Get options from form with defaults
    options = {
        'module_height': float(request.form.get('module_height', 15)),
        'module_width': float(request.form.get('module_width', 0.26)),
        'quiet_zone': float(request.form.get('quiet_zone', 6.5)),
        'font_size': int(request.form.get('font_size', 10)),
        'text_distance': float(request.form.get('text_distance', 5)),
        'center_text': True
    }
    
    # Save the barcode with options
    filepath = os.path.join(BARCODES_DIR, filename)
    code128.save(filepath, options)
    
    # Also save the data for other formats
    data_file = os.path.join(BARCODES_DIR, f"{filename}_data.txt")
    with open(data_file, 'w') as f:
        f.write(data)
    
    return filename

def generate_gs1_barcode_from_ais(gtin, lot_number, production_date):
    """
    Generate a GS1-128 barcode with the following Application Identifiers:
    - AI 01: GTIN (Global Trade Item Number)
    - AI 11: Production Date (YYMMDD)
    - AI 10: Lot Number (MMDDYY)
    """
    # Format the data with AIs
    data = f"(01){gtin}(11){production_date}(10){lot_number}"
    return generate_gs1_barcode(data)

@app.route('/download/<filename>/<format>')
def download_barcode(filename, format):
    """Handle barcode downloads in different formats"""
    format = format.upper()
    base_path = os.path.join(BARCODES_DIR, filename)
    
    if format == 'PNG':
        return send_file(base_path + '.png', 
                        mimetype='image/png',
                        as_attachment=True,
                        download_name=f'barcode.png')
    
    elif format == 'SVG':
        try:
            # Read the original data
            with open(base_path + '_data.txt', 'r') as f:
                data = f.read().strip()
            
            # Generate SVG version in memory
            writer = SVGWriter()
            code128 = Code128(data, writer=writer)
            svg_buffer = BytesIO()
            code128.write(svg_buffer)  # Write directly to buffer
            svg_buffer.seek(0)
            
            response = make_response(svg_buffer.getvalue())
            response.headers['Content-Type'] = 'image/svg+xml'
            response.headers['Content-Disposition'] = 'attachment; filename=barcode.svg'
            return response
            
        except Exception as e:
            return f"Error generating SVG: {str(e)}", 400
    
    elif format == 'EPS':
        # Generate EPS version using PIL
        with open(base_path + '.png', 'rb') as f:
            img = Image.open(f)
            eps_buffer = BytesIO()
            img.save(eps_buffer, 'EPS')
            eps_buffer.seek(0)
            
            response = make_response(eps_buffer.getvalue())
            response.headers['Content-Type'] = 'application/postscript'
            response.headers['Content-Disposition'] = 'attachment; filename=barcode.eps'
            return response
    
    return 'Invalid format', 400

@app.route('/', methods=['GET', 'POST'])
def index():
    barcode_path = None
    error = None
    filename = None
    
    if request.method == 'POST':
        try:
            # Check if using direct barcode input
            if 'full_barcode' in request.form and request.form['full_barcode'].strip():
                data = request.form['full_barcode'].strip()
                if not data:
                    error = "Please enter a barcode"
                else:
                    filename = generate_gs1_barcode(data)
                    barcode_path = url_for('static', filename=f'barcodes/{filename}.png')
            else:
                # Using AI-based input
                gtin = request.form.get('gtin', '').strip()
                lot_number = request.form.get('lot_number', '').strip()
                production_date = request.form.get('production_date', '').strip()
                
                # Basic validation
                if not gtin or not lot_number or not production_date:
                    error = "Please fill in all fields"
                elif not gtin.isdigit() or len(gtin) != 14:
                    error = "GTIN must be a 14-digit number"
                elif not lot_number.isdigit() or len(lot_number) != 6:
                    error = "Lot number must be in MMDDYY format"
                elif not production_date.isdigit() or len(production_date) != 6:
                    error = "Production date must be in YYMMDD format"
                else:
                    filename = generate_gs1_barcode_from_ais(gtin, lot_number, production_date)
                    barcode_path = url_for('static', filename=f'barcodes/{filename}.png')
                
        except Exception as e:
            error = str(e)
    
    return render_template('index.html', 
                         barcode_path=barcode_path, 
                         filename=filename,
                         error=error)

@app.before_request
def before_request():
    if not request.is_secure and app.env != 'development':
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port) 
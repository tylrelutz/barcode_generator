from flask import Flask, render_template, request, send_file, url_for, make_response, redirect
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

# GS1-128 Constants
FNC1 = chr(202)  # Function 1 symbol for GS1-128
FIXED_LENGTH_AIS = {
    '00': 18,  # SSCC
    '01': 14,  # GTIN
    '02': 14,  # GTIN of contained trade items
    '03': 14,  # GTIN of contained trade items
    '04': 16,  # GTIN
    '11': 6,   # Production date (YYMMDD)
    '12': 6,   # Due date (YYMMDD)
    '13': 6,   # Packaging date (YYMMDD)
    '14': 6,   # Best before date (YYMMDD)
    '15': 6,   # Best before date (YYMMDD)
    '16': 6,   # Sell by date (YYMMDD)
    '17': 6,   # Expiration date (YYMMDD)
    '18': 6,   # Production date (YYMMDD)
    '19': 6,   # Production date (YYMMDD)
    '20': 2,   # Product variant
    '31': 6,   # Net weight (kg)
    '32': 6,   # Net weight (kg)
    '33': 6,   # Net weight (kg)
    '34': 6,   # Net weight (kg)
    '35': 6,   # Net weight (kg)
    '36': 6,   # Net weight (kg)
    '41': 6    # Customer's purchase order number
}

# Ensure the barcodes directory exists
BARCODES_DIR = Path(app.config['UPLOAD_FOLDER'])
BARCODES_DIR.mkdir(parents=True, exist_ok=True)

def format_gs1_data(data):
    """
    Format data according to GS1-128 specifications:
    1. Add FNC1 at the start
    2. Add FNC1 between variable length fields
    3. Validate AI lengths
    """
    if not data.startswith('('):
        return data  # Return as is if it's not using AI format
        
    formatted_data = FNC1  # Start with FNC1
    current_pos = 0
    
    while current_pos < len(data):
        if data[current_pos] != '(':
            current_pos += 1
            continue
            
        # Extract AI
        ai_start = current_pos + 1
        ai_end = data.find(')', ai_start)
        if ai_end == -1:
            raise ValueError("Invalid AI format: missing closing parenthesis")
            
        ai = data[ai_start:ai_end]
        if not ai.isdigit():
            raise ValueError(f"Invalid AI: {ai}")
            
        # Add the AI with parentheses
        formatted_data += data[current_pos:ai_end + 1]
        
        # Find the start of the next AI or end of string
        next_ai_pos = data.find('(', ai_end + 1)
        if next_ai_pos == -1:
            next_ai_pos = len(data)
            
        # Get the value for this AI
        value = data[ai_end + 1:next_ai_pos]
        
        # Validate fixed-length AIs
        if ai in FIXED_LENGTH_AIS:
            expected_length = FIXED_LENGTH_AIS[ai]
            if len(value) != expected_length:
                raise ValueError(f"AI {ai} requires exactly {expected_length} characters")
        
        # Add the value
        formatted_data += value
        
        # If this is a variable length AI and not the last field, add FNC1
        if ai not in FIXED_LENGTH_AIS and next_ai_pos < len(data):
            formatted_data += FNC1
            
        current_pos = next_ai_pos
    
    return formatted_data

def generate_gs1_barcode(data):
    """
    Generate a GS1-128 barcode from the provided data
    """
    try:
        # Format data according to GS1-128 specifications
        formatted_data = format_gs1_data(data)
    except ValueError as e:
        raise ValueError(f"GS1-128 format error: {str(e)}")
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"gs1_128_{timestamp}"
    
    # Create the barcode writer (always use PNG for preview)
    writer = ImageWriter()
    code128 = Code128(formatted_data, writer=writer)
    
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
        f.write(formatted_data)
    
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
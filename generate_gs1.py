from barcode import Code128
from barcode.writer import ImageWriter
from datetime import datetime
import os

def generate_gs1_barcode(gtin, expiry_date, production_date, output_dir='barcodes'):
    """
    Generate a GS1-128 barcode with the following Application Identifiers:
    - AI 01: GTIN (Global Trade Item Number)
    - AI 11: Production Date
    - AI 10: Expiry Date
    
    Args:
        gtin (str): 14-digit GTIN number
        expiry_date (str): Expiry date in YYYYMMDD format
        production_date (str): Production date in YYYYMMDD format
        output_dir (str): Directory to save the generated barcode
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Format the data with AIs
    # AI 01: GTIN
    # AI 11: Production Date
    # AI 10: Expiry Date
    data = f"(01){gtin}(11){production_date}(10){expiry_date}"
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"gs1_128_{timestamp}"
    
    # Create the barcode
    code128 = Code128(data, writer=ImageWriter())
    
    # Save the barcode
    filepath = os.path.join(output_dir, filename)
    code128.save(filepath)
    print(f"Barcode saved as: {filepath}.png")

if __name__ == "__main__":
    # Example usage
    gtin = "12345678901234"  # 14-digit GTIN
    expiry_date = "20251231"  # Format: YYYYMMDD
    production_date = "20240315"  # Format: YYYYMMDD
    
    generate_gs1_barcode(gtin, expiry_date, production_date) 
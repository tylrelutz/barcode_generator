# GS1-128 Barcode Generator

A web application for generating GS1-128 barcodes with support for Application Identifiers (AIs) and multiple export formats (PNG, SVG, EPS).

## Features

- Generate GS1-128 barcodes with AI support
- Direct barcode data input or structured input (GTIN, Production Date, Lot Number)
- Multiple export formats (PNG, SVG, EPS)
- Customizable barcode parameters (height, width, font size, etc.)
- Mobile-friendly interface

## Local Development

1. Clone the repository:
```bash
git clone <your-repo-url>
cd gs1-barcode-generator
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5001`

## Deployment

### Deploy to Render

1. Create a Render account at https://render.com

2. Create a new Web Service:
   - Connect your GitHub repository
   - Select Python environment
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`

3. Set environment variables:
   - `SECRET_KEY`: A secure random string
   - `UPLOAD_FOLDER`: Path for barcode storage (default: static/barcodes)

### Alternative Deployment Options

The application can also be deployed to:
- Heroku
- DigitalOcean App Platform
- AWS Elastic Beanstalk

See the documentation for each platform for specific deployment instructions.

## Environment Variables

- `PORT`: Server port (default: 5001)
- `SECRET_KEY`: Flask secret key
- `UPLOAD_FOLDER`: Directory for storing generated barcodes

## License

MIT License 
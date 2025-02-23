# UPB Admitere Data Scraper

This application scrapes admission data from UPB (Universitatea Politehnica București) websites and displays it in a web interface.

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the web server:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

The application will display two tables:
- Current registration status (Stadiu Inscrieri)
- Pre-registration status (Stadiu Preinscrieri)

The data is fetched from:
- https://admitere.pub.ro/Admitere/site/stadiuInscrieri
- https://admitere.pub.ro/Admitere/site/stadiuPreinscrieri 
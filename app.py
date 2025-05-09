from flask import Flask, render_template_string
import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib3

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

def get_session_cookies(base_url="https://admitere.pub.ro"):
    # Headers to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    # First get the main page to get initial cookies
    session = requests.Session()
    session.headers.update(headers)
    session.verify = False
    
    # Step 1: Select București center
    select_center = session.get(f"{base_url}/Admitere/site/alegeCentru?idCentru=1")
    print(f"Center selection status: {select_center.status_code}")
    
    # Step 2: Select the "Licență 2025 B.I scris" session
    select_session = session.get(f"{base_url}/Admitere/site/alegeSesiune?idSesiune=79")
    print(f"Session selection status: {select_session.status_code}")
    
    return session

def scrape_table(url):
    try:
        # Create a session and select center and session
        session = get_session_cookies()
        
        # Now get the actual statistics page
        response = session.get(url)
        response.raise_for_status()
        # Set the correct encoding
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Print all tables found in the HTML
        all_tables = soup.find_all('table')
        print(f"\nNumber of tables found: {len(all_tables)}")
        for idx, t in enumerate(all_tables):
            print(f"\nTable {idx + 1} classes: {t.get('class', [])}")
            print(f"First 200 characters of table {idx + 1}:")
            print(str(t)[:200])
        
        # Try different ways to find the table
        table = None
        # Method 1: Find by class combination
        table = soup.find('table', class_=['table', 'table-bordered', 'table-condensed', 'table-responsive'])
        # Method 2: Find by class contains
        if not table:
            for t in soup.find_all('table'):
                if 'table-bordered' in (t.get('class', []) if isinstance(t.get('class', []), list) else [t.get('class', '')]):
                    table = t
                    break
        # Method 3: Find first table
        if not table:
            table = soup.find('table')
            
        if table:
            # Manually set column headers
            column_headers = ['Facultatea', 'Nr. Inscrieri']
            # Manually set row headers
            row_headers = ['Automatica si Calculatoare', 'Electronica, Telecomunicatii si Tehnologia Informatiei']
            
            # Extract rows
            rows = []
            for tr in table.find_all('tr'):
                row = []
                # Skip rows with class 'hide'
                if 'hide' in (tr.get('class', []) if isinstance(tr.get('class', []), list) else [tr.get('class', '')]):
                    continue
                    
                for td in tr.find_all(['td', 'th']):
                    # Get text from links if present, otherwise get cell text
                    cell_content = td.find('a')
                    if cell_content:
                        row.append(cell_content.text.strip())
                    else:
                        row.append(td.text.strip())
                if row and not all(cell == '' for cell in row):  # Skip empty rows
                    rows.append(row)
            
            print(f"\nNumber of rows found: {len(rows)}")
            if rows:
                print("First row:", rows[0])
            
            # Create DataFrame with the correct row headers
            if len(rows) > 1:  # Make sure we have data rows beyond headers
                df = pd.DataFrame(rows[1:], columns=column_headers)
                return df
        
        print("\nNo table found with the specified classes.")
        print("All classes found in the HTML:")
        for element in soup.find_all(class_=True):
            print(f"Element: {element.name}, Classes: {element['class']}")
        
        return pd.DataFrame(columns=['Facultatea', 'Nr. Inscrieri'])  # Return empty DataFrame if no table found
    except Exception as e:
        print(f"Error details: {str(e)}")
        return pd.DataFrame(columns=['Facultatea', 'Nr. Inscrieri'])  # Return empty DataFrame if an error occurs

def get_available_spots():
    # Create a DataFrame with the available spots
    data = {
        'Facultatea': [
            'Automatică și Calculatoare',
            'Automatică și Calculatoare',
            'Electronică, Telecomunicații și Tehnologia Informației',
            'Electronică, Telecomunicații și Tehnologia Informației',
            'Electronică, Telecomunicații și Tehnologia Informației'
        ],
        'Program': [
            'CTI Calculatoare și Tehnologia Informației',
            'IS Ingineria sistemelor',
            'IETTI Inginerie electronică, telecomunicații și tehnologii informaționale',
            'IETTI(E) Inginerie electronică, telecomunicații și tehnologii informaționale - engleză',
            'CTI Calculatoare și Tehnologia Informației'
        ],
        'Cod': [
            'AC-CTI-B',
            'AC-IS-B',
            'ETTI-IETTI-B',
            'ETTI-IETTI(E)-B',
            'ETTI-CTI-B'
        ],
        'Locuri disponibile': [
            165,
            125,
            250,
            60,
            60
        ]
    }
    df = pd.DataFrame(data)
    
    # Calculate totals per faculty - ensure exact faculty names match
    faculty_totals = df.groupby('Facultatea')['Locuri disponibile'].sum().reset_index()
    faculty_totals.columns = ['Facultatea', 'Total locuri disponibile']
    
    # Print debug information
    print("\nDebug - Faculty totals after calculation:")
    print(faculty_totals)
    
    # Normalize faculty names to use consistent characters
    df['Facultatea'] = df['Facultatea'].apply(lambda x: x.replace('ș', 'ş').replace('ț', 'ţ'))
    faculty_totals['Facultatea'] = faculty_totals['Facultatea'].apply(lambda x: x.replace('ș', 'ş').replace('ț', 'ţ'))
    
    return df, faculty_totals

def calculate_competition_ratio(total_df, faculty_totals_df):
    # Print input data for debugging
    print("\nDebug - Input data:")
    print("Total DF:")
    print(total_df)
    print("\nFaculty Totals DF:")
    print(faculty_totals_df)
    
    # Normalize faculty names in both dataframes
    total_df['Facultatea'] = total_df['Facultatea'].str.strip()
    faculty_totals_df['Facultatea'] = faculty_totals_df['Facultatea'].str.strip()
    
    # Convert special characters to match
    total_df['Facultatea'] = total_df['Facultatea'].apply(lambda x: x.replace('ș', 'ş').replace('ț', 'ţ'))
    faculty_totals_df['Facultatea'] = faculty_totals_df['Facultatea'].apply(lambda x: x.replace('ș', 'ş').replace('ț', 'ţ'))
    
    # Merge the dataframes
    competition_df = pd.merge(
        total_df[['Facultatea', 'Total Inscrieri']], 
        faculty_totals_df,
        on='Facultatea',
        how='left'
    )
    
    # Print merged data for debugging
    print("\nDebug - After merge:")
    print(competition_df)
    
    # Ensure numeric types
    competition_df['Total Inscrieri'] = pd.to_numeric(competition_df['Total Inscrieri'])
    competition_df['Total locuri disponibile'] = pd.to_numeric(competition_df['Total locuri disponibile'])
    
    # Calculate ratio
    competition_df['Candidati per loc'] = (
        competition_df['Total Inscrieri'] / competition_df['Total locuri disponibile']
    ).round(2)
    
    # Print final result for debugging
    print("\nDebug - Final competition DF:")
    print(competition_df)
    
    return competition_df

@app.route('/')
def index():
    # URLs to scrape
    inscrieri_url = "https://admitere.pub.ro/Admitere/site/stadiuInscrieri"
    preinscrieri_url = "https://admitere.pub.ro/Admitere/site/stadiuPreinscrieri"
    
    # Scrape both tables
    inscrieri_df = scrape_table(inscrieri_url)
    preinscrieri_df = scrape_table(preinscrieri_url)
    
    # Convert 'Nr. Inscrieri' to numeric, replacing any non-numeric values with 0
    inscrieri_df['Nr. Inscrieri'] = pd.to_numeric(inscrieri_df['Nr. Inscrieri'], errors='coerce').fillna(0)
    preinscrieri_df['Nr. Inscrieri'] = pd.to_numeric(preinscrieri_df['Nr. Inscrieri'], errors='coerce').fillna(0)
    
    # Calculate totals
    total_df = pd.merge(inscrieri_df, preinscrieri_df, on='Facultatea', suffixes=('_inscrieri', '_preinscrieri'))
    # Rename the columns
    total_df = total_df.rename(columns={
        'Nr. Inscrieri_inscrieri': 'Nr Inscrieri Validate',
        'Nr. Inscrieri_preinscrieri': 'Nr Inscrieri Nevalidate'
    })
    total_df['Total Inscrieri'] = total_df['Nr Inscrieri Validate'] + total_df['Nr Inscrieri Nevalidate']
    
    # Convert DataFrames to HTML
    inscrieri_table = inscrieri_df.to_html(classes='table table-striped table-bordered', index=False)
    preinscrieri_table = preinscrieri_df.to_html(classes='table table-striped table-bordered', index=False)
    total_table = total_df.to_html(classes='table table-striped table-bordered', index=False)
    
    # Get available spots and faculty totals
    available_spots_df, faculty_totals_df = get_available_spots()
    
    # Print debug information
    print("\nDebug - Faculty Totals DataFrame:")
    print(faculty_totals_df.dtypes)
    print(faculty_totals_df)
    
    # Calculate competition ratio
    competition_df = calculate_competition_ratio(total_df, faculty_totals_df)
    
    competition_table = competition_df.to_html(
        classes='table table-striped table-bordered',
        index=False,
        float_format=lambda x: '{:.2f}'.format(x) if isinstance(x, float) else x
    )
    
    # HTML template
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>UPB Admitere Data</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { 
                padding: 20px; 
                font-size: 16px;
            }
            .table-container { 
                margin-bottom: 40px;
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
            }
            .table { 
                width: 100%; 
                margin-bottom: 1rem;
            }
            .table th { 
                background-color: #f8f9fa;
                position: sticky;
                top: 0;
                z-index: 1;
                font-size: 1.1rem;
                padding: 12px;
            }
            .table td {
                padding: 12px;
                font-size: 1rem;
            }
            .table-bordered { 
                border: 1px solid #dee2e6; 
            }
            .countdowns-container {
                display: flex;
                gap: 20px;
                margin-bottom: 30px;
                flex-wrap: wrap;
            }
            
            .countdown {
                flex: 1;
                min-width: 300px;
                background-color: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .countdown h2 {
                font-size: 1.5rem;
                margin-bottom: 15px;
                color: #333;
            }
            .countdown-number {
                font-size: 1.3rem;
                font-weight: bold;
                color: #0d6efd;
                display: flex;
                justify-content: center;
                flex-wrap: wrap;
                gap: 20px;
            }
            .countdown-unit {
                display: inline-block;
                min-width: 100px;
                padding: 10px;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            h1 {
                font-size: 2.5rem;
                margin-bottom: 30px;
                color: #333;
            }
            h2 {
                font-size: 1.8rem;
                margin-bottom: 20px;
                color: #444;
            }
            
            /* Desktop-specific styles */
            @media (min-width: 1200px) {
                .container-fluid {
                    max-width: 1400px;
                    margin: 0 auto;
                }
                .table {
                    white-space: normal;
                }
                body {
                    padding: 30px;
                }
                .countdown {
                    min-width: 350px;
                }
            }
            
            /* Tablet-specific styles */
            @media (min-width: 769px) and (max-width: 1199px) {
                body {
                    padding: 20px;
                }
                h1 {
                    font-size: 2rem;
                }
                h2 {
                    font-size: 1.5rem;
                }
                .countdown h2 {
                    font-size: 1.3rem;
                }
                .countdown-number {
                    font-size: 1.2rem;
                }
                .countdown {
                    min-width: 300px;
                }
            }
            
            /* Mobile-specific styles */
            @media (max-width: 768px) {
                body {
                    padding: 10px;
                }
                .countdowns-container {
                    flex-direction: column;
                    gap: 15px;
                }
                .countdown {
                    min-width: 100%;
                }
                .countdown-number {
                    font-size: 1rem;
                }
                .countdown-unit {
                    min-width: 70px;
                    padding: 5px;
                }
                .table {
                    font-size: 13px;
                    white-space: nowrap;
                }
                h1 {
                    font-size: 1.75rem;
                }
                h2 {
                    font-size: 1.25rem;
                }
                .table th, .table td {
                    padding: 8px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container-fluid">
            <div class="countdowns-container">
                <div class="countdown" id="countdown-simulare">
                    <h2>Simulare</h2>
                    <div class="countdown-number">
                        <div class="countdown-unit"><span id="days-simulare">0</span> zile</div>
                        <div class="countdown-unit"><span id="hours-simulare">0</span> ore</div>
                        <div class="countdown-unit"><span id="minutes-simulare">0</span> minute</div>
                        <div class="countdown-unit"><span id="seconds-simulare">0</span> sec</div>
                    </div>
                </div>

                <div class="countdown" id="countdown-inscrieri">
                    <h2>Încheierea Înscrierilor</h2>
                    <div class="countdown-number">
                        <div class="countdown-unit"><span id="days-inscrieri">0</span> zile</div>
                        <div class="countdown-unit"><span id="hours-inscrieri">0</span> ore</div>
                        <div class="countdown-unit"><span id="minutes-inscrieri">0</span> minute</div>
                        <div class="countdown-unit"><span id="seconds-inscrieri">0</span> sec</div>
                    </div>
                </div>

                <div class="countdown" id="countdown-preadmitere">
                    <h2>Preadmitere</h2>
                    <div class="countdown-number">
                        <div class="countdown-unit"><span id="days-preadmitere">0</span> zile</div>
                        <div class="countdown-unit"><span id="hours-preadmitere">0</span> ore</div>
                        <div class="countdown-unit"><span id="minutes-preadmitere">0</span> minute</div>
                        <div class="countdown-unit"><span id="seconds-preadmitere">0</span> sec</div>
                    </div>
                </div>
            </div>

            <h1>UPB Admitere Data</h1>
            
            <div class="table-container">
                <h2>Total Inscrieri per Facultate</h2>
                {{ total_table | safe }}
            </div>

             <div class="table-container">
                <h2>Total Locuri Disponibile per Facultate</h2>
                {{ faculty_totals_table | safe }}
            </div>
                        
            <div class="table-container">
                <h2>Raport Candidati per Loc</h2>
                {{ competition_table | safe }}
            </div>

            <div class="table-container">
                <h2>Locuri Disponibile per Program</h2>
                {{ available_spots_table | safe }}
            </div>

        </div>

        <script>
            function createCountdown(targetDate, idPrefix) {
                const countDownDate = new Date(targetDate).getTime();

                return setInterval(function() {
                    const now = new Date().getTime();
                    const distance = countDownDate - now;

                    const days = Math.floor(distance / (1000 * 60 * 60 * 24));
                    const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                    const seconds = Math.floor((distance % (1000 * 60)) / 1000);

                    document.getElementById(`days-${idPrefix}`).textContent = days;
                    document.getElementById(`hours-${idPrefix}`).textContent = hours;
                    document.getElementById(`minutes-${idPrefix}`).textContent = minutes;
                    document.getElementById(`seconds-${idPrefix}`).textContent = seconds;

                    if (distance < 0) {
                        clearInterval(this);
                        document.getElementById(`countdown-${idPrefix}`).innerHTML = `<h2>Evenimentul a început!</h2>`;
                    }
                }, 1000);
            }

            // Create countdowns for all three events
            createCountdown("Mar 15, 2025 00:00:00", "simulare");
            createCountdown("Mar 30, 2025 00:00:00", "inscrieri");
            createCountdown("Apr 5, 2025 00:00:00", "preadmitere");
        </script>
    </body>
    </html>
    """
    
    from datetime import datetime
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return render_template_string(
        html_template,
        available_spots_table=available_spots_df.to_html(
            classes='table table-striped table-bordered', 
            index=False
        ),
        faculty_totals_table=faculty_totals_df.to_html(
            classes='table table-striped table-bordered',
            index=False
        ),
        inscrieri_table=inscrieri_table,
        preinscrieri_table=preinscrieri_table,
        total_table=total_table,
        competition_table=competition_table,
        current_time=current_time
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 
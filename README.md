# Evidence Collector and Validator

OCR-based misconfiguration scanner for EC&V (Essential Eight & Compliance & Verification).

This tool scans screenshots of system settings (e.g., Windows Features) and detects signs of non-compliance or misconfigurations across selected Essential Eight strategies using OCR and keyword matching.

---

## How It Works

- You provide screenshots (most image format e.g. PNG, JPG) of system configurations.
- The script uses **Tesseract OCR** to extract visible text.
- It checks for misconfiguration indicators using keyword rules for each strategy.
- Outputs findings into a CSV report: `scan_report.csv`.

---

## Strategies Supported

1. Application Control 
2. Patch Applications 
3. Configure Miscrosoft Office Macro Settings  
4. User Application Hardening
5. Restrict Administrative Privileges
6. Patch Operating Systems
7. Multi-Factor Authentication
8. Regular Backups

---

## Folder Structure

essential8_scanner/
├── screenshots/ # Place your PNG screenshots here
├── scanner.py # Main Python scanner
├── run_scanner.bat # Double-click to run easily
├── requirements.txt # Python dependencies
└── scan_report.csv # Output file (auto-generated)

Required Installs (once only):
1. Python (should already have this)
      Make sure to tick "Add to PATH" during install

2. Tesseract OCR
      Download: https://github.com/tesseract-ocr/tesseract
      Install Windows installer (scroll down to find .exe)
      Add the install path (e.g. C:\Program Files\Tesseract-OCR) to their System PATH
   
**after all that is installed you can run run it manualy by:**
cd path\to\essential8_scanner
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python scanner.py

**or you can double click the run_scanner.bat that i have added just to make it easier**

**for both these options first put your screen shot inside the screenshots/ folder**  **VERY IMPORTANT**

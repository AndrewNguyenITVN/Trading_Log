# Trading Journal System

A desktop application for traders to log, manage, analyze, and evaluate their trading performance. The system runs locally and provides a web-based interface for an intuitive user experience.

## Features

- Comprehensive trade logging
- Performance analysis and statistics
- Trade discipline tracking
- Security and portability
- Local data storage
- Interactive dashboard
- Customizable interface

## Setup Instructions

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
- Windows:
```bash
.\venv\Scripts\activate
```
- macOS/Linux:
```bash
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Access the application:
Open your web browser and navigate to `http://localhost:5000`

## Project Structure

```
trading_journal/
├── app.py                 # Main application file
├── config.py             # Configuration settings
├── requirements.txt      # Project dependencies
├── static/              # Static files (CSS, JS, images)
├── templates/           # HTML templates
├── models/             # Database models
├── utils/              # Utility functions
└── data/              # Data storage
```

## Data Storage

All data is stored locally in SQLite database. The database file is located in the `data` directory.

## Backup and Restore

The system supports backup and restore functionality. Backups include both the database and uploaded images.

## License

This project is licensed under the MIT License. 
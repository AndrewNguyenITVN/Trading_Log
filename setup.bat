@echo off
echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate

echo Installing dependencies...
pip install -r requirements.txt

python generate_fake_data.py

echo Setup complete!
echo To start the application, run: python app.py
pause 


script build python: build.py
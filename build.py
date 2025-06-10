import PyInstaller.__main__
import os
import shutil

# The name for your application
APP_NAME = "TradingJournal"

def get_path(path):
    """
    Helper function to get the correct path for bundled data files.
    """
    return os.path.join(os.path.dirname(__file__), path)

if __name__ == '__main__':
    # Define the PyInstaller command
    # --noconfirm: Overwrite output without asking
    # --onefile: Create a single executable file
    # --windowed: Do not create a console window
    # --add-data: Bundle data files (templates, static)
    pyinstaller_command = [
        'app.py',
        '--noconfirm',
        '--onefile',
        '--windowed',
        f'--name={APP_NAME}',
        f'--add-data={get_path("templates")}{os.pathsep}templates',
        f'--add-data={get_path("static")}{os.pathsep}static',
    ]

    print(f"Running PyInstaller with command: {' '.join(pyinstaller_command)}")

    # Execute PyInstaller
    PyInstaller.__main__.run(pyinstaller_command)

    print("\n\nBuild complete.")
    print(f"Executable is located in the '{get_path('dist')}' folder.") 
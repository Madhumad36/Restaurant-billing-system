 
import os
from utils.db_utils import setup_database
from ui.main_ui import main  # import main function

def ensure_folders():
    for folder in ['db', 'data', 'ui', 'utils']:
        if not os.path.exists(folder):
            os.makedirs(folder)

if __name__ == '__main__':
    ensure_folders()
    setup_database()
    main()   # call main() here instead of start_gui()

from droidrun_gui.main_window import main
import sys
import os

def get_portal_apk_path():
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'resources', 'droidrun-portal-v0.1.1.apk')
    else:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "droidrun-portal-v0.1.1.apk"))
PORTAL_APK_PATH = get_portal_apk_path()

if __name__ == "__main__":
    main() 
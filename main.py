import sys
import customtkinter as ctk

# Set global appearance before initializing the app
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

def check_dependencies():
    missing = []
    try:
        import yt_dlp
    except ImportError:
        missing.append("yt-dlp")
    
    try:
        import requests
    except ImportError:
        missing.append("requests")
        
    try:
        import PIL
    except ImportError:
        missing.append("Pillow")
        
    if missing:
        print(f"Missing required dependencies: {', '.join(missing)}")
        print("Please install them using: pip install -r requirements.txt")
        sys.exit(1)

def main():
    check_dependencies()
    
    from ui import AppUI
    
    app = AppUI()
    app.mainloop()

if __name__ == "__main__":
    main()

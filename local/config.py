import json
from pathlib import Path

def load_settings() -> dict[str, str|int|tuple[int,int]|bool]:
    '''Returns a dictionary containing the required settings for the application.
    If a "settings.json" file exists in the main directory, then the setting are loaded 
    from there, else the settings file is created with the default settings.
    '''

    settings = { 
        "FONT_NAME": "Arial",
        "FONT_SIZE" : 12,
        "STYLE" : "bold",  # For no style use empty string: ""
        "TEXT_COLOR" : "#eee3e3",
        "NOTIFICATION_COLOR" : "red",
        "TIMESTAMP_COLOR" : "red",
        "USERNAME_COLOR" : "orange",
        "BG_COLOR" : "#202020",
        "MEMBER_BG_COLOR" : "blue",
        "SUPERCHAT_BG_COLOR" : "green",
        "HIGHLIGHT_USER_BG_COLOR": "grey",
        "EMOTE_SIZE" : (24, 24),
        "CHAT_LENGTH" : 30,  # Reducing this increases performance.
        "DISABLE_TITLEBAR" : False,  # If True, then no window resizing after running the app.
        "WINDOW_SIZE" : (480, 640),  # If 'DISABLE_TITLEBAR' is True, set the window size (width, height).
        "TRANSPARENT" : False,
        "ALPHA" : 0.7,  # Change to 1 or None if TRANSPARENT is True.
        "OFF_FOCUS_EVENTS": True,
        "CONDENSED": True,  # Limits the empty lines in the chat window. 
        "SHOW_TIMESTAMP": False  # Whether to show timestamp next to username.
    }

    current_directory = Path(__file__).parent if "__file__" in locals() else Path.cwd()

    try:
        settings_file = list(current_directory.glob("settings.json"))[0]
        with open(settings_file, "r") as file:
            settings = json.load(file)
    except IndexError:  # No settings.json present.
        with open("settings.json", "w") as file:
            json.dump(settings, file, indent=4)
    return settings
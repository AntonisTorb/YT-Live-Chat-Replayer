import base64
from collections import deque
from datetime import datetime as dt
from datetime import timedelta
from pathlib import Path
import sys
import tkinter as tk

import local.chat as chat
import local.config as config
import local.user_messages as user_messages

from PIL.ImageTk import PhotoImage
from pynput.keyboard import Key, Listener  # pip install pynput
import PySimpleGUI as sg  # pip install PySimpleGUI


key_event = False  # Global var used to track if the Play/Pause/Resume key was pressed, since GUI and event listener are in different threads.
off_focus_events = True  # Global var used to turn on/off off-focus event listener.


def on_press(key:str) -> None:
    '''Modify the global variable "key_event" if the specified play/pause key is pressed.'''

    global key_event
    global off_focus_events
    if key == Key.space and off_focus_events:
        key_event = False if key_event else True


def listen_kb() -> None:
    '''Event listener for keyboard events. Needs to be in a separate thread to the GUI, so they can coexist.'''

    with Listener(on_press=on_press) as listener:
        listener.join()


def get_icon():
    try:
        with open("images/icon.png", "rb") as image_file:
            return base64.b64encode(image_file.read())
    except FileNotFoundError:
        return None


def data_selection_window(settings:dict[str, str|int|tuple[int,int]|bool]) -> dict[str, bool|Path|None]:
    '''Creates a window where the user can enter the paths to the required chat json file,
    as well as optionally select a local emote directory and a text containing usernames 
    to highlight in chat. The selections are returned in the "data" dictionary.
    '''

    data = {
        "exit": True,
        "json path": None,
        "use local emotes": False,
        "emote dir path": None,
        "highlight users": False,
        "user path": None
    }

    layout = [
        [
            sg.Text("Select the JSON file:", background_color=settings["BG_COLOR"]), 
            sg.Input("", readonly=True, key="-JSON_PATH-", expand_x=True), 
            sg.Button("Browse", key="-BROWSE_JSON-")
        ],
        [
            sg.Checkbox("Use local emote images from directory:", key="-USE_LOCAL_EMOTES-", 
                        enable_events=True, background_color=settings["BG_COLOR"]),
            sg.Input("", readonly=True, key="-EMOTE_PATH-", expand_x=True), 
            sg.Button("Browse", key="-BROWSE_EMOTE-")
        ],
        [
            sg.Checkbox("Highlight users in file:", key="-HIGHLIGHT_USERS-", 
                        enable_events=True, background_color=settings["BG_COLOR"]), 
            sg.Input("", readonly=True, key="-USER_PATH-", expand_x=True), 
            sg.Button("Browse", key="-BROWSE_USER_HIGHLIGHT-")
        ],
        [sg.Button("Start"), sg.Push(background_color=settings["BG_COLOR"]), sg.Button("Exit")]
    ]

    data_window = sg.Window("Data selection",layout, enable_close_attempted_event=True, icon=get_icon(),
                            font=(settings["FONT_NAME"], settings["FONT_SIZE"], settings["STYLE"]), 
                            resizable=False, background_color=settings["BG_COLOR"], finalize=True)
    
    while True:
        event, values = data_window.read()

        match event:
            case sg.WIN_CLOSE_ATTEMPTED_EVENT | "Exit":
                break
            case "-BROWSE_JSON-":
                json_to_load = sg.popup_get_file('', no_window= True, file_types=(("JSON file", "*.json*"),))
                if json_to_load:
                    data_window["-JSON_PATH-"].update(json_to_load)
                    data["json path"] = Path(json_to_load)
            case "-BROWSE_EMOTE-":
                emote_directory = sg.popup_get_folder('', no_window= True)
                if emote_directory:
                    data_window["-EMOTE_PATH-"].update(emote_directory)
                    data["emote dir path"] = Path(emote_directory)
            case "-BROWSE_USER_HIGHLIGHT-":
                users_to_highlight = sg.popup_get_file('', no_window= True, file_types=(("text file", "*.txt*"),))
                if users_to_highlight:
                    data_window["-USER_PATH-"].update(users_to_highlight)
                    data["user path"] = Path(users_to_highlight)
            case "-USE_LOCAL_EMOTES-":
                data["use local emotes"] = True if values["-USE_LOCAL_EMOTES-"] else False
            case "-HIGHLIGHT_USERS-":
                data["highlight users"] = True if values["-HIGHLIGHT_USERS-"] else False
            case "Start":
                if data["json path"] is None:
                    user_messages.one_line_error_handler("Please specify the JSON file path.", settings)
                elif data["use local emotes"] and data["emote dir path"] is None:
                    user_messages.one_line_error_handler("Please specify the emote directory.", settings)
                elif data["highlight users"] and data["user path"] is None:
                    user_messages.one_line_error_handler("Please specify the username file.", settings)
                else:
                    data["exit"] = False
                    break
    data_window.close()
    return data


def display_chat(chat_window:sg.Multiline, 
                 comment_deque:deque[tuple[str, str, tuple[str, str]]]|list[tuple[str, str, tuple[str, str]]], 
                 emote_images:dict[str,PhotoImage], 
                 settings:dict[str, str|int|tuple[int,int]|bool], 
                 usernames_to_highlight:list[str]) -> None:
    '''Displays the chat based on the current timestamp to the chat window.
    Also displays the negative timestamp chat items at startup.
    '''
    
    if not comment_deque:
        return
    chat_window.update("")
    for comment in comment_deque:
        if "membership" not in comment[2][0] and "superchat" not in comment[2][0]:
            bg_color = settings["BG_COLOR"]
        elif "membership" in comment[2][0]:
            bg_color = settings["MEMBER_BG_COLOR"]
        elif "superchat" in comment[2][0]:
            bg_color = settings["SUPERCHAT_BG_COLOR"]
        if usernames_to_highlight:
            if comment[1] in usernames_to_highlight:
                bg_color = settings["HIGHLIGHT_USER_BG_COLOR"]

        chat_window.update(f"{comment[0]:<12} ", append=True, 
                        text_color_for_value=settings["TIMESTAMP_COLOR"], 
                        background_color_for_value=bg_color)
        chat_window.update(f"{comment[1]}\n", append=True, 
                        text_color_for_value=settings["USERNAME_COLOR"], 
                        background_color_for_value=bg_color)
        for message_type, message_content in comment[2]:
            if message_type == "text":
                chat_window.update(f"{message_content} ", append=True, 
                                    text_color_for_value=settings["TEXT_COLOR"], 
                                    background_color_for_value=bg_color)
            elif message_type == "emoji":
                emote_img = message_content
                if emote_img in emote_images.keys():
                    # No parameter for background color in tk.Text.image_create...
                    # chat_window.widget.configure(bg=bg_color) # Nope, worse...
                    _ = chat_window.image_create(tk.INSERT, emote_img, padx=2)
                else:
                    chat_window.update(f"{message_content} ", append=True, 
                                    text_color_for_value=settings["TEXT_COLOR"], 
                                    background_color_for_value=bg_color)
            elif message_type == "membership" or message_type == "superchat":
                chat_window.update(f"{message_content} ", append=True, 
                                    text_color_for_value=settings["TEXT_COLOR"], 
                                    background_color_for_value=bg_color)
            
        chat_window.update("\n", append=True, 
                        text_color_for_value=settings["TEXT_COLOR"], 
                        background_color_for_value=bg_color)
        chat_window.update("\n", append=True, 
                        text_color_for_value=settings["TEXT_COLOR"], 
                        background_color_for_value=settings["BG_COLOR"])


def main_window() -> None:
    '''Main window construction and logic loop.'''
    
    settings = config.load_settings()
    data = data_selection_window(settings)
    
    if data["exit"]:
        sys.exit(0)
    
    playing = False
    paused_timestamp = None # timedelta(hours=0, minutes=12,seconds=25)
    
    emote_link_dict = {}
    if data["use local emotes"]:
        local_emote_list = list(data["emote dir path"].glob("*.png"))
        local_emote_names = [emote.name[:-4] for emote in local_emote_list]
        comments = chat.get_comments(data["json path"], emote_link_dict, local_emote_names)
    else: 
        comments = chat.get_comments(data["json path"], emote_link_dict)

    if data["highlight users"]:
        with open(data["user path"], "r") as file:
            usernames_to_highlight = [user[:-1] if user.endswith("\n") else user for user in file.readlines()]
    else:
        usernames_to_highlight = []

    comment_deque = deque("", maxlen=settings["CHAT_LENGTH"])
    
    class Multiline(sg.Multiline):
        '''Subclass so we can define the method necessary to display emotes in the Multiline element.'''

        def image_create(self, index:str, key:str, padx:int=None, pady:int=None) -> str:
            if key in emote_images:
                image = emote_images[key]
                name = self.widget.image_create(index, image=image, padx=padx, pady=pady)
                return name

    layout = [
        [sg.Text("Chat Replay")],
        [Multiline("", expand_x=True, expand_y=True, background_color=settings["BG_COLOR"], 
                    text_color= settings["TEXT_COLOR"], autoscroll=True, write_only=True, disabled=True, key="-CHAT-")],
        [
            sg.Button("⏵", key="-PLAY_PAUSE-"), sg.Button("⏹", key="-STOP-"), 
            sg.Push(background_color=settings["BG_COLOR"]),
            sg.Spin([i for i in range(24)], initial_value=0, size=(2,1), 
                    background_color=settings["BG_COLOR"], text_color=settings["TEXT_COLOR"], key="-HR-"), 
            sg.Spin([i for i in range(60)], initial_value=0, size=(2,1), 
                    background_color=settings["BG_COLOR"], text_color=settings["TEXT_COLOR"], key="-MIN-"), 
            sg.Spin([i for i in range(60)], initial_value=0, size=(2,1), 
                    background_color=settings["BG_COLOR"], text_color=settings["TEXT_COLOR"], key="-SEC-"), 
            sg.Button("Go"),
            sg.Checkbox("Off-focus events", key="-OFF_FOCUS_EVENTS-", 
                        default=True, enable_events=True, background_color=settings["BG_COLOR"]),
            sg.Push(background_color=settings["BG_COLOR"]), sg.Button("Exit")
        ]
    ]

    transparent_color = settings["BG_COLOR"] if settings["TRANSPARENT"] else None

    window = sg.Window("Youtube Live Chat Replay", layout, size=(480,640), margins=(0,0), element_padding=(0,0),
                    font=(settings["FONT_NAME"], settings["FONT_SIZE"], settings["STYLE"]), grab_anywhere=True,
                    resizable=True, enable_close_attempted_event=True, sbar_trough_color=settings["BG_COLOR"],
                    no_titlebar=settings["DISABLE_TITLEBAR"], keep_on_top=True, background_color=settings["BG_COLOR"],
                    transparent_color=transparent_color, alpha_channel=settings["ALPHA"], icon=get_icon(), finalize=True)
    # window.set_min_size((480, 640))

    if settings["DISABLE_TITLEBAR"]:
        window.size = settings["WINDOW_SIZE"]
    chat_window = window["-CHAT-"]
    
    chat_window.update("Getting emotes from web, please wait...\n", append=True, 
                                    text_color_for_value=settings["NOTIFICATION_COLOR"], 
                                    background_color_for_value=settings["BG_COLOR"])
    window.refresh()

    if data["use local emotes"]:
        emote_images = chat.prepare_emotes(emote_link_dict, settings["EMOTE_SIZE"], local_emote_list)
    else:
        emote_images = chat.prepare_emotes(emote_link_dict, settings["EMOTE_SIZE"])

    temp_list = []
    for timestamp, comment_list in comments.items():
        if not timestamp.startswith("-"):
            break
        for comment in comment_list:
            if comment in temp_list:
                continue
            temp_list.append(comment)
        if temp_list:
            display_chat(chat_window, temp_list, emote_images, settings, usernames_to_highlight)
    del(temp_list)

    while True:

        global key_event
        if key_event:
            event = "-PLAY_PAUSE-"
            _, values = window.read(timeout=250)
            key_event = False
        else:
            event, values = window.read(timeout=250)
        
        # if event != "__TIMEOUT__":
        #     print(event)
        
        if playing:
            cur_time = dt.now()
            if paused_timestamp is not None:
                chat_timestamp_dt = cur_time - start_time + paused_timestamp
            else:
                chat_timestamp_dt = cur_time - start_time
            
            chat_timestamp = str(chat_timestamp_dt).split(".", 2)[0]
            if len(chat_timestamp) == 7:
                chat_timestamp = f"0{chat_timestamp}"
            
            hr, min, sec = tuple(chat_timestamp.split(":"))
            window["-HR-"].update(hr)
            window["-MIN-"].update(min)
            window["-SEC-"].update(sec)

            comment_deque = chat.get_chat(comments, comment_deque, chat_timestamp)
            display_chat(chat_window, comment_deque, emote_images, settings, usernames_to_highlight)
                
        match event:
            case sg.WIN_CLOSE_ATTEMPTED_EVENT | "Exit":
                break
            case "-PLAY_PAUSE-":
                if not playing:
                    playing = True
                    window["-PLAY_PAUSE-"].update("⏸")
                    start_time = dt.now()
                elif playing:
                    playing = False
                    window["-PLAY_PAUSE-"].update("⏵")
                    paused_timestamp = chat_timestamp_dt
            case "-STOP-":
                playing = False
                paused_timestamp = None
                comment_deque.clear()

                window["-PLAY_PAUSE-"].update("⏵")
                window["-HR-"].update(0)
                window["-MIN-"].update(0)
                window["-SEC-"].update(0)
            case "Go":
                if playing:
                    playing = False
                    window["-PLAY_PAUSE-"].update("⏵")
                    paused_timestamp = chat_timestamp_dt

                try:
                    hr = int(values["-HR-"])
                    min = int(values["-MIN-"])
                    sec = int(values["-SEC-"])
                
                    if hr in range(24) and min in range(60) and sec in range(60):
                        paused_timestamp = timedelta(hours=int(hr), minutes=int(min),seconds=int(sec))
                    else:
                        chat_window.update("Please enter a correct time format.\n", append=True, 
                                    text_color_for_value=settings["NOTIFICATION_COLOR"], 
                                    background_color_for_value=settings["BG_COLOR"])
                    comment_deque.clear()
                except ValueError:
                    chat_window.update("Please enter a correct time format.\n", append=True, 
                                    text_color_for_value=settings["NOTIFICATION_COLOR"], 
                                    background_color_for_value=settings["BG_COLOR"])
            case "-OFF_FOCUS_EVENTS-":
                global off_focus_events
                off_focus_events = True if values["-OFF_FOCUS_EVENTS-"] else False
    window.close()
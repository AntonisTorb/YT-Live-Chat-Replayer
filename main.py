from collections import deque
from datetime import datetime as dt
from datetime import timedelta
import json
from pathlib import Path
import sys
import threading
import tkinter as tk

import local

from PIL import Image  # pip install Pillow
from PIL.ImageTk import PhotoImage
from PIL import UnidentifiedImageError
from pynput.keyboard import Key, Listener  # pip install pynput
import PySimpleGUI as sg  # pip install PySimpleGUI
import requests  # pip install requests


'''
For our most beloved kettle <3                                                                              
                                                     .#%%%(///#%%%*             
                                                   #%(            /%%           
                                                 ,%#                (%/         
                          ,*********/  ////////  %%      %%(/%%,     #%.        
                       ,#(        /%, (%,    %% .%#     (%*  .%#     /%,        
                       ##        .%/ ,%/     /%, #%.      #%%#.      %%         
                      /#.        ##  %#       #%. (%(              *%%          
                     ,#*        (#. #%         *%#  /%%/        *%%#            
                     #(        *#* /#,           /%#  %% *%%%%#/.               
                    (#.       .#( .#/           .%#  %# *%/                     
                   ,(*        (#  ##            #%%%%# *%%%%/                   
                   ((        /#. /#.                        #%                  
                  ((        ,#* ,#*           ##,,,,,,,,,,,,,.                  
                 *(,        ((  #(           (######%%%%%%%(                    
                .(/        /(  ((                      *##                      
                /(        ,(, *(.                    .##                        
               *(.        (/ .(((((((((###############.                         
              .(*        ((                                                     
              //        ................,.,,,,,,(#*                             
               *(////((((((((((((((((((((((.  *#/                               
                                        ,(* ,((                                 
                                       .(/.((                                   
                                       ((((.                                    
                                      /((,                                      
                                     *(*                                        
                                    ,/                                          
                                                                               
'''


key_event = False  # Global var used to track if the Play/Pause/Resume key was pressed, since GUI and event listener are in different threads.


def on_press(key:str) -> None:
    '''Modify the global variable "key_event" if the specified play/pause key is pressed.'''

    global key_event
    if key == Key.space:
        key_event = False if key_event else True


def listen_kb() -> None:
    '''Event listener for keyboard events. Needs to be in a separate thread to the GUI, so they can coexist.'''

    with Listener(on_press=on_press) as listener:
        listener.join()


def format_timestamp(timestamp:str) -> str:
    '''Return a formatted string timestamp (HH:MM:SS).'''

    if timestamp.startswith("-"):
        timestamp = f"-00:0{timestamp[1:]}"
    elif len(timestamp) == 4:
        timestamp = f"00:0{timestamp}"
    elif len(timestamp) == 5:
        timestamp = f"00:{timestamp}"
    elif len(timestamp) == 7:
        timestamp = f"0{timestamp}"
    return timestamp


def populate_emote_links(emote_txt:str, emote_link_dict:dict[str,str], local_emote_names:list[str], url:str) -> None:
    '''Populates a dictionary with the emote name as key and emote link as value for every unique emote.
    Svg images not supported by Pillow, so we will be using the emoji instead.
    '''

    if emote_txt in emote_link_dict.keys() or url.endswith("svg") or emote_txt in local_emote_names:
        return
    emote_link_dict[emote_txt] = url


def get_comments(filepath:str|Path, emote_link_dict:dict[str,str], emote_names:list[str] = []) -> dict[str, list[tuple[str,str,tuple[str,str]]]]:
    '''Get a dictionary of all comments with the timestamp as key, and a list of tuples as value.
    The values contain the timestamp, author of the message and the message as a tuple.
    The message tuple contains the message type (text, emoji, etc.) and the message content.
    '''

    with open(filepath, encoding="utf8") as file:
        data = file.readlines()
        chat_data = []
        for line in data:
            chat_data.append(json.loads(line))

    comments = {}
    for line in chat_data:#[0:1]:
        for action in line["replayChatItemAction"]["actions"]:
            if "addLiveChatTickerItemAction" in action:
                continue
            item = action["addChatItemAction"]["item"]
            amount = None
            if "liveChatTextMessageRenderer" in item:  # Normal chat.
                source = item["liveChatTextMessageRenderer"]
                message_list = source["message"]["runs"]
                timestamp = format_timestamp(source["timestampText"]["simpleText"])
                author = source["authorName"]["simpleText"]
            elif "liveChatMembershipItemRenderer" in item:  # Member.
                source = item["liveChatMembershipItemRenderer"]
                if "headerPrimaryText" in source:
                    message_list = source["headerPrimaryText"]["runs"]
                    if "message" in source:
                        member_message_list = source["message"]["runs"]
                else:
                    message_list = source["headerSubtext"]["runs"]
                timestamp = format_timestamp(source["timestampText"]["simpleText"])
                author = source["authorName"]["simpleText"]
            elif "liveChatPaidMessageRenderer" in item:  # Superchat.
                source = item["liveChatPaidMessageRenderer"]
                amount = source["purchaseAmountText"]["simpleText"]
                timestamp = format_timestamp(source["timestampText"]["simpleText"])
                author = source["authorName"]["simpleText"]
                try:
                    message_list = source["message"]["runs"]
                except KeyError:
                    message_list = []
            else:
                continue

            if amount:
                message = [("superchat", amount)]
            else:
                message = []

            # !!! need to refactor this, too much indented and duplicate code
            for message_dict in message_list:
                for message_type, message_segment in message_dict.items():
                    if message_type == "emoji":
                        if len(message_segment["emojiId"]) <= 2:
                            emote_txt = message_segment["emojiId"]
                            populate_emote_links(emote_txt, emote_link_dict, emote_names, message_segment["image"]["thumbnails"][0]["url"])
                        else:
                            try:  # custom emote
                                emote_txt = message_segment["searchTerms"][1]
                                populate_emote_links(emote_txt, emote_link_dict, emote_names, message_segment["image"]["thumbnails"][0]["url"])
                            except IndexError:
                                emote_txt = message_segment["searchTerms"][0]
                                populate_emote_links(emote_txt, emote_link_dict, emote_names, message_segment["image"]["thumbnails"][0]["url"])
                        message.append((message_type, emote_txt))
                    elif "liveChatMembershipItemRenderer" in item and message_type == "text":
                        message.append(("membership", message_segment))
                    elif message_type == "text":
                        message.append((message_type, message_segment))
            try:  # For membership messages.
                for message_dict in member_message_list:
                    for message_type, message_segment in message_dict.items():
                        if message_type == "emoji":
                            if len(message_segment["emojiId"]) <= 2:
                                emote_txt = message_segment["emojiId"]
                                populate_emote_links(emote_txt, emote_link_dict, emote_names, message_segment["image"]["thumbnails"][0]["url"])
                            else:
                                try:  # custom emote
                                    emote_txt = message_segment["searchTerms"][1]
                                    populate_emote_links(emote_txt, emote_link_dict, emote_names, message_segment["image"]["thumbnails"][0]["url"])
                                except IndexError:
                                    emote_txt = message_segment["searchTerms"][0]
                                    populate_emote_links(emote_txt, emote_link_dict, emote_names, message_segment["image"]["thumbnails"][0]["url"])
                            message.append((message_type, emote_txt))
                        elif message_type == "text":
                            message.append((message_type, message_segment))
                member_message_list = []
            except UnboundLocalError:
                pass
            
            if timestamp in comments.keys():
                comments[timestamp].append((timestamp, author, message))
            else:
                comments[timestamp] = [(timestamp, author, message)]

    return comments


def get_chat(comments:dict[str, list[tuple[str,str,tuple[str,str]]]], 
            comment_deque:deque[tuple[str, str, tuple[str, str]]], 
            chat_timestamp:str) -> deque[tuple[str, str, tuple[str, str]]]:
    '''Returns a deque of comments that need to be displayed according to the current chat timestamp.'''

    if chat_timestamp in comments.keys():
        for comment in comments[chat_timestamp]:
            if comment in comment_deque:
                continue
            comment_deque.append(comment)
    return comment_deque


def prepare_emotes(emote_link_dict:dict[str,str], emote_size:tuple[int,int], local_emote_list:list[Path]=[]) -> dict[str,PhotoImage]:
    '''Produces a dictionary with the emote name as key and a PhotoImage object containing 
    the emote image so it can be displayed in the chat window.
    '''

    if local_emote_list:
        emote_images_pil = {filepath.name[:-4]: Image.open(filepath).resize(emote_size) for filepath in local_emote_list}
    else:
       emote_images_pil = {} 

    for emote_name, link in emote_link_dict.items():
        if link.endswith(".svg"):
            continue
        try:
            emote_images_pil[emote_name] = Image.open(requests.get(link, stream=True).raw).resize(emote_size)
        except UnidentifiedImageError:
            pass

    return {name: PhotoImage(image=image) for name, image in emote_images_pil.items()}


def load_settings() -> dict[str, str|int|tuple[int,int]|bool]:
    '''Returns a dictionary containing the required settings for the application.
    If a "settings.json" file exists in the main directory, then the setting are loaded from there,
    else the settings file is created with the default settings.
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
        "PLAY_PAUSE_KEY" : "space",
        "DISABLE_TITLEBAR" : True,  # If True, then no window resizing after running the app.
        "WINDOW_SIZE" : (480, 640),  # If 'DISABLE_TITLEBAR' is True, set the window size (width, height).
        "TRANSPARENT" : False,
        "ALPHA" : 0.7  # Change to 1 or None if TRANSPARENT is True.
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


def data_selection_window(settings:dict[str, str|int|tuple[int,int]|bool]) -> dict[str, bool|Path|None]:
    '''Creates a window where the user can enter the paths to the required chat json file, as well as optionally
    select a local emote directory and a text containing usernames to highlight in chat. The selections are returned
    in the "data" dictionary.
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
            sg.Input("", readonly=True, key="-JSON_PATH-"), 
            sg.Button("Browse", key="-BROWSE_JSON-")
        ],
        [
            sg.Checkbox("Use local emote images from directory:", key="-USE_LOCAL_EMOTES-", 
                        enable_events=True, background_color=settings["BG_COLOR"]),
            sg.Input("", readonly=True, key="-EMOTE_PATH-"), 
            sg.Button("Browse", key="-BROWSE_EMOTE-")
        ],
        [
            sg.Checkbox("Highlight users in file:", key="-HIGHLIGHT_USERS-", 
                        enable_events=True, background_color=settings["BG_COLOR"]), 
            sg.Input("", readonly=True, key="-USER_PATH-"), 
            sg.Button("Browse", key="-BROWSE_USER_HIGHLIGHT-")
        ],
        [sg.Button("Start"), sg.Push(background_color=settings["BG_COLOR"]), sg.Button("Exit")]
    ]

    data_window = sg.Window("Data selection",layout, enable_close_attempted_event=True,
                            font=(settings["FONT_NAME"], settings["FONT_SIZE"], settings["STYLE"]), 
                            resizable=True, background_color=settings["BG_COLOR"], finalize=True)
    
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
                    local.one_line_error_handler("Please specify the JSON file path.", settings)
                elif data["use local emotes"] and data["emote dir path"] is None:
                    local.one_line_error_handler("Please specify the emote directory.", settings)
                elif data["highlight users"] and data["user path"] is None:
                    local.one_line_error_handler("Please specify the username file.", settings)
                else:
                    data["exit"] = False
                    break
    data_window.close()
    return data


def main_window() -> None:
    '''Main window construction and logic loop.'''
    
    settings = load_settings()
    data = data_selection_window(settings)
    
    if data["exit"]:
        sys.exit(0)
    
    playing = False
    paused_timestamp = None # timedelta(hours=0, minutes=12,seconds=25)
    
    emote_link_dict = {}
    if data["use local emotes"]:
        local_emote_list = list(data["emote dir path"].glob("*.png"))
        local_emote_names = [emote.name[:-4] for emote in local_emote_list]
        comments = get_comments(data["json path"], emote_link_dict, local_emote_names)
    else: 
        comments = get_comments(data["json path"], emote_link_dict)
    
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
            sg.Button("Play", key="-PLAY_PAUSE-"), sg.Push(background_color=settings["BG_COLOR"]), 
            sg.Spin([i for i in range(24)], initial_value=0, size=(2,1), 
                    background_color=settings["BG_COLOR"], text_color=settings["TEXT_COLOR"], key="-HR-"), 
            sg.Spin([i for i in range(60)], initial_value=0, size=(2,1), 
                    background_color=settings["BG_COLOR"], text_color=settings["TEXT_COLOR"], key="-MIN-"), 
            sg.Spin([i for i in range(60)], initial_value=0, size=(2,1), 
                    background_color=settings["BG_COLOR"], text_color=settings["TEXT_COLOR"], key="-SEC-"), 
            sg.Button("Go"),
            sg.Push(background_color=settings["BG_COLOR"]), sg.Button("Exit")
        ]
    ]

    transparent_color = settings["BG_COLOR"] if settings["TRANSPARENT"] else None

    window = sg.Window("Youtube Live Chat Replay", layout, size=(480,640), margins=(0,0), element_padding=(0,0),
                    font=(settings["FONT_NAME"], settings["FONT_SIZE"], settings["STYLE"]), grab_anywhere=True,
                    resizable=True, enable_close_attempted_event=True, sbar_trough_color=settings["BG_COLOR"],
                    no_titlebar=settings["DISABLE_TITLEBAR"], keep_on_top=True, background_color=settings["BG_COLOR"],
                    transparent_color=transparent_color, alpha_channel=settings["ALPHA"], finalize=True)
    # window.set_min_size((480, 640))

    if settings["DISABLE_TITLEBAR"]:
        window.size = settings["WINDOW_SIZE"]
    chat_window = window["-CHAT-"]
    
    chat_window.update("Getting emotes from web, please wait...\n", append=True, 
                                    text_color_for_value=settings["NOTIFICATION_COLOR"], 
                                    background_color_for_value=settings["BG_COLOR"])
    window.refresh()

    if data["use local emotes"]:
        emote_images = prepare_emotes(emote_link_dict, settings["EMOTE_SIZE"], local_emote_list)
    else:
        emote_images = prepare_emotes(emote_link_dict, settings["EMOTE_SIZE"])
    
    chat_window.update("Ready to play!\n", append=True, 
                                    text_color_for_value=settings["NOTIFICATION_COLOR"], 
                                    background_color_for_value=settings["BG_COLOR"])
    
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
        
        cur_time = dt.now()
        if playing:
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
            comment_deque = get_chat(comments, comment_deque, chat_timestamp)
            if comment_deque:
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
                
        match event:
            case sg.WIN_CLOSE_ATTEMPTED_EVENT | "Exit":
                break
            case "-PLAY_PAUSE-":
                if not playing:
                    playing = True
                    window["-PLAY_PAUSE-"].update("Pause")
                    start_time = dt.now()
                elif playing:
                    playing = False
                    window["-PLAY_PAUSE-"].update("Resume")
                    paused_timestamp = chat_timestamp_dt
            case "Go":
                if playing:
                    playing = False
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
                except ValueError:
                    chat_window.update("Please enter a correct time format.\n", append=True, 
                                    text_color_for_value=settings["NOTIFICATION_COLOR"], 
                                    background_color_for_value=settings["BG_COLOR"])
    window.close()


def main() -> None:
    '''Main function.'''
    
    threading.Thread(target=main_window).start()
    threading.Thread(target=listen_kb, daemon=True).start() 


if __name__ == "__main__":
    
    main()
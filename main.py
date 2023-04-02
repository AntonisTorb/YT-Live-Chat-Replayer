from collections import deque
from datetime import datetime as dt
from datetime import timedelta
import json
from pathlib import Path
import threading
import tkinter as tk

from PIL import Image
from PIL.ImageTk import PhotoImage
from PIL import UnidentifiedImageError
from pynput.keyboard import Key, Listener
import PySimpleGUI as sg
import requests


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


FILENAME = "test.json"
FONT_NAME = "Arial"
FONT_SIZE = 12
STYLE = "bold" # For no style use empty string: ""
TEXT_COLOR = "#eee3e3"
TIMESTAMP_COLOR = "red"
USERNAME_COLOR = "orange"
BG_COLOR = "#202020"
MEMBER_BG_COLOR = "blue"
SUPERCHAT_BG_COLOR = "green"
EMOTE_SIZE = (24, 24)
CHAT_LENGTH = 30 # Reducing this increadses perfiormance.
PLAY_PAUSE_KEY = Key.space
DISABLE_TITLEBAR = True # If True, then no window resizing after running the app.
WINDOW_SIZE = (480, 640) # If 'DISABLE_TITLEBAR' is True, set the window size (width, height)
TRANSPARENT = False
ALPHA = 0.7 # Change to 1 or None if TRANSPARENT is True.

key_event = False # Global var used to track if the Play/Pause/Resume key was pressed, since GUI and event listener are in different threads.


def on_press(key:Key) -> None:
    '''Modify the global variable "key_event" if the specified play/pause key is pressed.'''

    global key_event
    if key == PLAY_PAUSE_KEY:
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


def populate_emote_links(emote_txt:str, emote_link_dict:dict[str,str], url:str) -> None:
    '''Populates a dictionary with the emote name as key and emote link as value for every unique emote.
    Svg images not supported by Pillow, so we will be using the emoji instead.
    '''

    if emote_txt not in emote_link_dict.keys() and not url.endswith("svg"):
        emote_link_dict[emote_txt] = url


def get_comments(filepath:str|Path, emote_link_dict:dict[str,str]) -> dict[str, list[tuple[str,str,tuple[str,str]]]]:
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
    for line in chat_data:#[1780:1810]:
        for action in line["replayChatItemAction"]["actions"]:
            if "addLiveChatTickerItemAction" in action:
                continue
            item = action["addChatItemAction"]["item"]
            amount = None
            if "liveChatTextMessageRenderer" in item: # Normal chat.
                source = item["liveChatTextMessageRenderer"]
                message_list = source["message"]["runs"]
                timestamp = format_timestamp(source["timestampText"]["simpleText"])
                author = source["authorName"]["simpleText"]
            elif "liveChatMembershipItemRenderer" in item: # Member.
                source = item["liveChatMembershipItemRenderer"]
                if "headerPrimaryText" in source:
                    message_list = source["headerPrimaryText"]["runs"]
                    if "message" in source:
                        member_message_list = source["message"]["runs"]
                else:
                    message_list = source["headerSubtext"]["runs"]
                timestamp = format_timestamp(source["timestampText"]["simpleText"])
                author = source["authorName"]["simpleText"]
            elif "liveChatPaidMessageRenderer" in item: # Superchat.
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

            for message_dict in message_list:
                for message_type, message_segment in message_dict.items():
                    if message_type == "emoji":
                        if len(message_segment["emojiId"]) <= 2:
                            emote_txt = message_segment["emojiId"]
                            populate_emote_links(emote_txt, emote_link_dict, message_segment["image"]["thumbnails"][0]["url"])
                        else:
                            try: # custom emote
                                emote_txt = message_segment["searchTerms"][1]
                                populate_emote_links(emote_txt, emote_link_dict, message_segment["image"]["thumbnails"][0]["url"])
                            except IndexError:
                                emote_txt = message_segment["searchTerms"][0]
                                populate_emote_links(emote_txt, emote_link_dict, message_segment["image"]["thumbnails"][0]["url"])
                        message.append((message_type, emote_txt))
                    elif "liveChatMembershipItemRenderer" in item and message_type == "text":
                        message.append(("membership", message_segment))
                    elif message_type == "text":
                        message.append((message_type, message_segment))
            try: # For membership messages.
                for message_dict in member_message_list:
                    for message_type, message_segment in message_dict.items():
                        if message_type == "emoji":
                            if len(message_segment["emojiId"]) <= 2:
                                emote_txt = message_segment["emojiId"]
                                populate_emote_links(emote_txt, emote_link_dict, message_segment["image"]["thumbnails"][0]["url"])
                            else:
                                try: # custom emote
                                    emote_txt = message_segment["searchTerms"][1]
                                    populate_emote_links(emote_txt, emote_link_dict, message_segment["image"]["thumbnails"][0]["url"])
                                except IndexError:
                                    emote_txt = message_segment["searchTerms"][0]
                                    populate_emote_links(emote_txt, emote_link_dict, message_segment["image"]["thumbnails"][0]["url"])
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

def prepare_emotes(emote_link_dict:dict[str,str]) -> dict[str,PhotoImage]:
    '''Produces a dictionary with the emote name as key and a PhotoImage object containing 
    the emote image so it can be displayed in the chat window.
    '''

    emote_images_pil = {}
    for emote_name, link in emote_link_dict.items():
        if link.endswith(".svg"):
            continue
        try:
            emote_images_pil[emote_name] = Image.open(requests.get(link, stream=True).raw).resize(EMOTE_SIZE)
        except UnidentifiedImageError:
            pass

    # emote_images_pil = {filepath.name[:-4]: Image.open(str(filepath)).resize(EMOTE_SIZE) for filepath in emote_list}
    
    # for filepath in emote_list:
    #     emote_images_pil[filepath.name[:-4]] = Image.open(str(filepath)).resize(EMOTE_SIZE)

    return {name: PhotoImage(image=image) for name, image in emote_images_pil.items()}


def main_window() -> None:
    '''Main window construction and logic loop.'''
    
    playing = False
    paused_timestamp = None #timedelta(hours=2, minutes=14,seconds=50)
    emote_link_dict = {}
    comments = get_comments(FILENAME, emote_link_dict)

    comment_deque = deque("", maxlen=CHAT_LENGTH)

    emote_list = list(Path("emotes").glob("*.png"))
    emote_names = [emote.name[:-4] for emote in emote_list]
    
    class Multiline(sg.Multiline):
        '''Subclass so we can define the method necessary to display emotes in the Multiline element.'''

        def image_create(self, index:str, key:str, padx:int=None, pady:int=None) -> str:
            if key in emote_images:
                image = emote_images[key]
                name = self.widget.image_create(index, image=image, padx=padx, pady=pady)
                return name

    layout = [
        [sg.Text("Chat Replay")],
        [Multiline("", expand_x=True, expand_y=True, background_color=BG_COLOR, 
                    text_color= TEXT_COLOR, autoscroll=True, write_only=True, disabled=True, key="-CHAT-")],
        [sg.Button("Play", key="-PLAY_PAUSE-"), sg.Push(), sg.Button("Exit")]
    ]

    transparent_color = BG_COLOR if TRANSPARENT else None

    window = sg.Window("Youtube Live Chat Replay", layout, size=(480,640), font=(FONT_NAME, FONT_SIZE, STYLE), 
                    resizable=True, enable_close_attempted_event=True, sbar_trough_color=BG_COLOR,
                    no_titlebar=DISABLE_TITLEBAR, grab_anywhere=True, keep_on_top=True, background_color=BG_COLOR,
                    transparent_color=transparent_color, margins=(0,0), element_padding=(0,0), alpha_channel=ALPHA,finalize=True)
    #window.set_min_size((480, 640))
    if DISABLE_TITLEBAR:
        window.size = WINDOW_SIZE
    chat_window = window["-CHAT-"]
    
    chat_window.update("Getting emotes from web, please wait...\n", 
                                    append=True, 
                                    text_color_for_value=TIMESTAMP_COLOR, 
                                    background_color_for_value=BG_COLOR)
    window.refresh()

    emote_images = prepare_emotes(emote_link_dict)
    
    chat_window.update("Ready to play!\n", 
                                    append=True, 
                                    text_color_for_value=TIMESTAMP_COLOR, 
                                    background_color_for_value=BG_COLOR)
    
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
            comment_deque = get_chat(comments, comment_deque, chat_timestamp)
            if comment_deque:
                chat_window.update("")
                for comment in comment_deque:
                    if "membership" not in comment[2][0] and "superchat" not in comment[2][0]:
                        bg_color = BG_COLOR
                    elif "membership" in comment[2][0]:
                        bg_color = MEMBER_BG_COLOR
                    elif "superchat" in comment[2][0]:
                        bg_color = SUPERCHAT_BG_COLOR

                    chat_window.update(f"{comment[0]:<12} ", 
                                    append=True, 
                                    text_color_for_value=TIMESTAMP_COLOR, 
                                    background_color_for_value=bg_color)
                    chat_window.update(f"{comment[1]}\n", 
                                    append=True, 
                                    text_color_for_value=USERNAME_COLOR, 
                                    background_color_for_value=bg_color)
                    for message_type, message_content in comment[2]:
                        if message_type == "text":
                            chat_window.update(
                                f"{message_content} ", append=True, text_color_for_value=TEXT_COLOR, 
                                background_color_for_value=bg_color
                            )
                        elif message_type == "emoji":
                            emote_img = message_content
                            if emote_img in emote_images.keys():
                                _ = chat_window.image_create(tk.INSERT, emote_img, padx=2)
                            else:
                                chat_window.update(f"{message_content} ", 
                                                append=True, 
                                                text_color_for_value=TEXT_COLOR, 
                                                background_color_for_value=bg_color)
                        elif message_type == "membership" or message_type == "superchat":
                            chat_window.update(
                                f"{message_content} ", append=True, text_color_for_value=TEXT_COLOR, 
                                background_color_for_value=bg_color
                            )

                    chat_window.update("\n", append=True, 
                                    text_color_for_value=TEXT_COLOR, background_color_for_value=bg_color)
                    chat_window.update("\n", append=True, 
                                    text_color_for_value=TEXT_COLOR, background_color_for_value=BG_COLOR)

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
    window.close()

def main():
    threading.Thread(target=main_window).start()
    threading.Thread(target=listen_kb, daemon=True).start() 

if __name__ == "__main__":
    
    main()
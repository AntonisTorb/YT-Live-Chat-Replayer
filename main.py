import PySimpleGUI as sg
from datetime import datetime as dt
import json
from collections import deque

TEXT_COLOR = "#eee3e3"
BG_COLOR = "#202020"

with open("test.json", encoding="utf8") as file:
    data = file.readlines()
    chat_data = []
    for line in data:
        chat_data.append(json.loads(line))

comments = {}

for line in chat_data:#[2:150]:
    for action in line["replayChatItemAction"]["actions"]:
        try:
            item = action["addChatItemAction"]["item"]
            try:
                source = item["liveChatTextMessageRenderer"]
            except KeyError:
                pass
            try:
                timestamp = source["timestampText"]["simpleText"]
                if timestamp.startswith("-"):
                    timestamp = f"-00:0{timestamp[1:]}"
                elif len(timestamp) == 4:
                    timestamp = f"00:0{timestamp}"
                elif len(timestamp) == 5:
                    timestamp = f"00:{timestamp}"
                elif len(timestamp) == 7:
                    timestamp = f"0{timestamp}"
                author = source["authorName"]["simpleText"]
                message = ""
                message_list = source["message"]["runs"]
                for message_dict in message_list:
                    for message_type, message_segment in message_dict.items():
                        if message_type == "emoji":
                            try: # custom emote
                                add_txt = message_segment["shortcuts"][1]
                            except IndexError:
                                add_txt = message_segment["shortcuts"][0]
                            message = f"{message}{add_txt} "
                        elif message_type == "text":
                            message = f"{message}{message_segment} "
                if timestamp in comments.keys():
                    comments[timestamp].append((timestamp, author, message))
                else:
                    comments[timestamp] = [(timestamp, author, message)]
            except NameError:
                pass
        except KeyError:
            pass

#print(comments)

playing = False
comment_deque =  deque("", maxlen=30)

layout = [
    [sg.Text("Chat Replay")],
    [sg.Multiline("", expand_x=True, expand_y=True, background_color=BG_COLOR, 
                  text_color= TEXT_COLOR, autoscroll=True, write_only=True, disabled=True, key="-CHAT-")],
    [sg.Button("Play", key="-PLAY_PAUSE-"), sg.Push(), sg.Button("Exit")]
]

window = sg.Window("Youtube Live Chat Replay", layout, size=(480, 640), font=("Arial", 12), 
                   resizable=True, enable_close_attempted_event=True, finalize=True)
#window.set_min_size((480, 640))

def get_chat(comments, comment_deque, delta_t):
    try:
        for comment in comments[delta_t]:
            if comment not in comment_deque:
                comment_deque.append(comment)
        
        #print(comment_deque)
        return comment_deque
    except KeyError:
        return comment_deque

while True:
    event, values = window.read(timeout=250)
    cur_time = dt.now()
    if playing:
        delta_t = str(cur_time - start_time).split(".", 2)[0]
        if len(delta_t) == 7:
            delta_t = f"0{delta_t}"
        comment_deque = get_chat(comments, comment_deque, delta_t)
        if comment_deque:
            window["-CHAT-"].update("")
            for comment in comment_deque:
                window["-CHAT-"].update(f"{comment[0]:<12} ", append=True, text_color_for_value="red", background_color_for_value=BG_COLOR)
                window["-CHAT-"].update(f"{comment[1]}\n", append=True, text_color_for_value="green", background_color_for_value=BG_COLOR)
                window["-CHAT-"].update(f"{comment[2]}\n\n", append=True, text_color_for_value=TEXT_COLOR, background_color_for_value=BG_COLOR)

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
                # add pause logic and time tracking to resume
window.close()
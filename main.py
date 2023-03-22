import PySimpleGUI as sg
from datetime import datetime as dt
import json

with open("test.json", encoding="utf8") as file:
    data = file.readlines()
    chat_data = []
    for line in data:
        chat_data.append(json.loads(line))

comments = [] # make this into dict

for line in chat_data[0:150]:
    for action in line["replayChatItemAction"]["actions"]:
        try:
            item = action["addChatItemAction"]["item"]
            try:
                source = item["liveChatTextMessageRenderer"]
            except KeyError:
                pass
            try:
                timestamp = source["timestampText"]["simpleText"]
                author = source["authorName"]["simpleText"]
                message = ""
                message_list = source["message"]["runs"]
                for message_dict in message_list:

                    for message_type, message_segment in message_dict.items():
                        if message_type == "emoji":
                            try:
                                add_txt = message_segment["shortcuts"][1]
                            except IndexError:
                                add_txt = message_segment["shortcuts"][0]
                            message = f"{message}{add_txt} "
                        elif message_type == "text":
                            message = f"{message}{message_segment} "
                    
                comments.append((timestamp, author, message))
            except NameError:
                pass

        except KeyError:
            pass

new_bg = False

def get_bg(new_bg):
    if new_bg:
        return "#303030", False
    else:
        return "#202020", True

bg_col, new_bg = get_bg(new_bg)


layout = [
    [sg.Text("Chat Replay")],
    [sg.Multiline("", expand_x=True, expand_y=True, background_color=bg_col, 
                  text_color= "#eee3e3", autoscroll=True, write_only=True, disabled=True, reroute_stdout=True, key="-CHAT-")],
    [sg.Button("Exit"), sg.Button("Print")]
]

window = sg.Window("Youtube Live Chat Replay", layout, size=(480, 640), font=("Arial", 14), 
                   resizable=True, enable_close_attempted_event=True, finalize=True)
#window.set_min_size((480, 640))

for comment in comments:
    bg_col, new_bg = get_bg(new_bg) 
    #window["-CHAT-"].print(comment, colors=("#eee3e3",bg_col), autoscroll=True)


while True:
    event, values = window.read(timeout=100)
    cur_time = dt.now().strftime("%H:%M:%S")
    #print(cur_time)
    match event:
        case sg.WIN_CLOSE_ATTEMPTED_EVENT | "Exit":
            break
        case "Print":
            for comment in comments:
                bg_col, new_bg = get_bg(new_bg)
                if comment[0].startswith("-"):
                    timestamp = f"-00:0{comment[0][1:]}"
                elif len(comment[0]) == 4:
                    timestamp = f"00:0{comment[0]}"
                elif len(comment[0]) == 5:
                    timestamp = f"00:{comment[0]}"
                elif len(comment[0]) == 7:
                    timestamp = f"0{comment[0]}"
                else:
                    timestamp = comment[0]
                window["-CHAT-"].update(f"{timestamp:<12} ", append=True, text_color_for_value="red", background_color_for_value=bg_col)
                window["-CHAT-"].update(f"{comment[1]:<30} ", append=True, text_color_for_value="green", background_color_for_value=bg_col)
                window["-CHAT-"].update(f"{comment[2]} ", append=True, text_color_for_value="white", background_color_for_value=bg_col)
                window["-CHAT-"].update("\n", append=True, text_color_for_value="red", background_color_for_value=bg_col)
window.close()
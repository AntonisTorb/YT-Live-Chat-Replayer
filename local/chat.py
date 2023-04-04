from collections import deque
import json
from pathlib import Path
from typing import Any

from PIL import Image  # pip install Pillow
from PIL.ImageTk import PhotoImage
from PIL import UnidentifiedImageError
import requests  # pip install requests


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


def populate_emote_links(emote_txt:str, 
                         emote_link_dict:dict[str,str], 
                         local_emote_names:list[str], 
                         url:str) -> None:
    '''Populates a dictionary with the emote name as key and emote link as value for every 
    unique emote. Svg images not supported by Pillow, so we will be using the emoji instead.
    '''

    if emote_txt in emote_link_dict.keys() or url.endswith("svg") or emote_txt in local_emote_names:
        return
    emote_link_dict[emote_txt] = url


def determine_message_segment(emote_link_dict:dict[str,str], 
                              emote_names:list[str], 
                              message:list[tuple[str,str]], 
                              message_list:list[dict[str,Any]], 
                              item:dict[str,Any]={}) -> None:
    '''Determining the type of the message segment and appending the content to the message.
    For emotes, the names and links are saved, unless they exist in local file (if selected).
    '''

    for message_dict in message_list:
        for message_type, message_segment in message_dict.items():
            if message_type == "emoji":
                if len(message_segment["emojiId"]) <= 4:
                    emote_txt = message_segment["emojiId"]
                    populate_emote_links(emote_txt, emote_link_dict, emote_names, message_segment["image"]["thumbnails"][0]["url"])
                else:
                    try:  # custom emote
                        emote_txt = message_segment["searchTerms"][1]
                        populate_emote_links(emote_txt, emote_link_dict, emote_names, message_segment["image"]["thumbnails"][0]["url"])
                    except IndexError:
                        emote_txt = message_segment["searchTerms"][0]
                        populate_emote_links(emote_txt, emote_link_dict, emote_names, message_segment["image"]["thumbnails"][0]["url"])
                    except KeyError:  # Just in case
                        # print(len(message_segment["emojiId"]))
                        continue
                message.append((message_type, emote_txt))
            elif "liveChatMembershipItemRenderer" in item and message_type == "text":
                message.append(("membership", message_segment))
            elif message_type == "text":
                message.append((message_type, message_segment))


def get_comments(filepath:str|Path, 
                 emote_link_dict:dict[str,str], 
                 emote_names:list[str] = []) -> dict[str, list[tuple[str,str,tuple[str,str]]]]:
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
    member_message_list = []

    for line in chat_data:#[0:100]:
        action = line["replayChatItemAction"]["actions"][0]

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

        determine_message_segment(emote_link_dict, emote_names, message, message_list, item)
        if member_message_list:
            determine_message_segment(emote_link_dict, emote_names, message, member_message_list)
            member_message_list = []
        
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


def prepare_emotes(emote_link_dict:dict[str,str], 
                   emote_size:tuple[int,int], 
                   local_emote_list:list[Path]=[]) -> dict[str,PhotoImage]:
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
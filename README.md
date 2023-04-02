# YT Live Chat Replayer
A GUI app that can replay the live chat from a YouTube live stream, using the JSON file containing the chat data (obtained with [yt-dlp](https://github.com/yt-dlp/yt-dlp) for example).

# ! WARNING ! Early stages, not meant to be used yet! Also JSON file needs to be in condesed format to work (1 item per line)!



## Need to:
- ~~Generate a dict with the timestamp as key, tuple 0f comments as value.~~ Done.
- ~~Add `start`/`pause` button and proper time tracking.~~ Done.
- ~~Update the Multiline element with the most recent comments up to a limit (maybe use a `collections.deque` to keep it limited to avoid `if-else` statements for length?)~~ Done!
- Add option to jump to timestamp, rewind or go forward maybe?
- ~~Figure out if possible to display images in the Multiline so I can add emotes.~~ Done, need to add option to get from local file after adding the file selector.
- ~~Add display of superchat comments (`liveChatPaidMessageRenderer` instead of `liveChatTextMessageRenderer`).~~ Done!
- ~~Membership notifications/messages too maybe?~~ Done!
- File selector to specify the JSON file path and emote file path (optional).
- Option to have a different background/text color for comments from specific usernames (for example the streamer or a live translator).
- When starting the app, after selecting the filepaths and before playback, display all the chats with a negative timestamp.
- Properly refactor code for easier modification and performance (less loops would be nice, but the yt JSON is a bit messy).
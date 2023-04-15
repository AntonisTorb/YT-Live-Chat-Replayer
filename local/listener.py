import local.globals as globals

from pynput.keyboard import Key, Listener  # pip install pynput


def on_press(key:str) -> None:
    '''Modify the global variable "key_event" if the specified play/pause key is pressed.'''

    if key == Key.space and globals.off_focus_events:
        globals.key_event = False if globals.key_event else True


def listen_kb() -> None:
    '''Event listener for keyboard events. Needs to be in a separate thread to the GUI, so they can coexist.'''

    with Listener(on_press=on_press) as listener:
        listener.join()
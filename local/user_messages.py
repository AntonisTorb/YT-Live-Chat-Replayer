import PySimpleGUI as sg  # pip install PySimpleGUI


def one_line_error_handler(text: str, settings) -> None:
    '''Displays window with a short error message.'''

    sg.Window(
        "ERROR!", [
            [
                sg.Push(background_color=settings["BG_COLOR"]), 
                sg.Text(text,background_color=settings["BG_COLOR"]), 
                sg.Push(background_color=settings["BG_COLOR"])],
            [sg.Push(background_color=settings["BG_COLOR"]), sg.OK(), sg.Push(background_color=settings["BG_COLOR"])]
        ], 
        modal= True,
        background_color=settings["BG_COLOR"], 
        font=(settings["FONT_NAME"], settings["FONT_SIZE"])
    ).read(close= True)
import PySimpleGUI as sg

from model import convert_3_components


def main():
    sg.set_options(font='Cambria 12')
    col = [
        [sg.Push(), sg.Text('Input folder'), sg.Input(key='-IN-', size=(60, 10)), sg.Button('Choose', key='In')],
        [sg.Push(), sg.Text('Output folder'), sg.Input(key='-OUT-', size=(60, 10)), sg.Button('Choose', key='Out')],
        [sg.Button('Start'), sg.Exit()]
    ]
    layout = [[sg.Column(col, element_justification='c')]]
    window = sg.Window("SCOUT Convertor", layout)

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED or event == 'Exit':
            break

        if event == 'In':
            window['-IN-'].update(sg.popup_get_folder('Choose folder', no_window=True))

        if event == 'Out':
            window['-OUT-'].update(sg.popup_get_folder('Choose folder', no_window=True))

        if event == 'Start':
            path_in = window['-IN-'].get()
            path_out = window['-OUT-'].get()
            if path_in != '' and path_out != '':
                convert_3_components(path_in, path_out)


if __name__ == '__main__':
    main()

# main.py

import builtins
import io
import threading
import traceback
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from queue import Queue

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.codeinput import CodeInput
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserListView

try:
    from pygments.lexers import PythonLexer
except ImportError:
    PythonLexer = None


Window.clearcolor = (0.055, 0.065, 0.08, 1)


class PythonEditor(CodeInput):
    font_size = 16
    tab_width = 4
    write_tab = True
    auto_indent = True
    multiline = True

    background_color = (0.055, 0.065, 0.08, 1)
    foreground_color = (0.90, 0.92, 0.96, 1)
    cursor_color = (1, 1, 1, 1)
    selection_color = (0.20, 0.40, 0.70, 0.55)
    padding = [8, 8, 8, 8]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if PythonLexer:
            self.lexer = PythonLexer()

    def insert_text(self, substring, from_undo=False):

        pairs = {
            "(": ")",
            "[": "]",
            "{": "}",
            '"': '"',
            "'": "'"
        }

        closers = {
            ")",
            "]",
            "}",
            '"',
            "'"
        }

        if substring in pairs and not from_undo:

            row, col = self.cursor

            lines = self.text.split("\n")

            if row < len(lines):
                line = lines[row]

                if col < len(line):
                    next_char = line[col]

                    if substring in closers and next_char == substring:
                        self.do_cursor_movement("cursor_right")
                        return

            super().insert_text(
                substring + pairs[substring],
                from_undo=from_undo
            )

            self.do_cursor_movement("cursor_left")
            return

        if substring in closers and not from_undo:

            row, col = self.cursor
            lines = self.text.split("\n")

            if row < len(lines):

                line = lines[row]

                if col < len(line):
                    if line[col] == substring:
                        self.do_cursor_movement("cursor_right")
                        return

        super().insert_text(substring, from_undo=from_undo)


class TerminalInput(TextInput):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.multiline = False
        self.size_hint_y = None
        self.height = 42
        self.font_size = 16

        self.background_color = (0.08, 0.09, 0.11, 1)
        self.foreground_color = (0.95, 0.95, 0.95, 1)

        self.hint_text = "input() için buraya yaz ve Enter'a bas"

        self.callback = None

        self.bind(
            on_text_validate=self.submit
        )

    def submit(self, *args):

        if self.callback:

            value = self.text

            callback = self.callback

            self.callback = None

            self.text = ""

            callback(value)


class PythonIDE(BoxLayout):

    def __init__(self, **kwargs):

        super().__init__(
            orientation="vertical",
            spacing=4,
            padding=5,
            **kwargs
        )

        self.current_file = None
        self.running = False

        self.create_toolbar()
        self.create_editor()
        self.create_terminal()

    # -------------------------------------------------
    # TOOLBAR
    # -------------------------------------------------

    def create_toolbar(self):

        toolbar = BoxLayout(
            size_hint_y=None,
            height=48,
            spacing=4
        )

        buttons = [
            ("Yeni", self.new_file),
            ("Aç", self.open_file),
            ("Kaydet", self.save_file),
            ("▶ Çalıştır", self.run_code),
            ("■ Durdur", self.stop_code),
            ("Temizle", self.clear_output)
        ]

        for text, callback in buttons:

            button = Button(
                text=text,
                font_size=13
            )

            button.bind(
                on_release=callback
            )

            toolbar.add_widget(button)

        self.add_widget(toolbar)

    # -------------------------------------------------
    # EDITOR
    # -------------------------------------------------

    def create_editor(self):

        self.filename_label = Label(
            text="main.py",
            size_hint_y=None,
            height=28,
            halign="left",
            valign="middle"
        )

        self.filename_label.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", value)
        )

        self.add_widget(self.filename_label)

        self.editor = PythonEditor(
            text=(
                'print("PythonPocket IDE")\n'
                'isim = input("Adın: ")\n'
                'print("Merhaba", isim)\n'
            )
        )

        self.add_widget(
            self.editor
        )

    # -------------------------------------------------
    # TERMINAL
    # -------------------------------------------------

    def create_terminal(self):

        terminal_label = Label(
            text="TERMINAL / ÇIKTI",
            size_hint_y=None,
            height=28,
            halign="left"
        )

        terminal_label.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", value)
        )

        self.add_widget(
            terminal_label
        )

        self.output = TextInput(
            readonly=True,
            multiline=True,
            font_size=14,
            size_hint_y=0.28,
            background_color=(0.025, 0.03, 0.04, 1),
            foreground_color=(0.85, 0.92, 0.85, 1),
            padding=[8, 8]
        )

        self.add_widget(
            self.output
        )

        self.input_box = TerminalInput()

        self.add_widget(
            self.input_box
        )

        self.status = Label(
            text="Hazır",
            size_hint_y=None,
            height=24,
            halign="left"
        )

        self.status.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", value)
        )

        self.add_widget(
            self.status
        )

    # -------------------------------------------------
    # OUTPUT
    # -------------------------------------------------

    def output_text(self, text):

        def update(dt):

            self.output.text += str(text)

            self.output.cursor = (
                0,
                len(self.output.text)
            )

        Clock.schedule_once(update)

    # -------------------------------------------------
    # NEW FILE
    # -------------------------------------------------

    def new_file(self, *args):

        if self.running:
            return

        self.editor.text = ""

        self.current_file = None

        self.filename_label.text = "main.py"

        self.status.text = "Yeni dosya"

    # -------------------------------------------------
    # SAVE
    # -------------------------------------------------

    def save_file(self, *args):

        if self.current_file:

            try:

                Path(
                    self.current_file
                ).write_text(
                    self.editor.text,
                    encoding="utf-8"
                )

                self.status.text = (
                    "Kaydedildi: "
                    + Path(self.current_file).name
                )

            except Exception as e:

                self.output_text(
                    "\nKaydetme hatası:\n"
                    + str(e)
                    + "\n"
                )

        else:

            self.save_as()

    # -------------------------------------------------
    # SAVE AS
    # -------------------------------------------------

    def save_as(self):

        layout = BoxLayout(
            orientation="vertical",
            spacing=8,
            padding=10
        )

        name = TextInput(
            text="main.py",
            multiline=False,
            size_hint_y=None,
            height=45
        )

        buttons = BoxLayout(
            size_hint_y=None,
            height=45,
            spacing=5
        )

        save_button = Button(
            text="Kaydet"
        )

        cancel_button = Button(
            text="İptal"
        )

        buttons.add_widget(
            save_button
        )

        buttons.add_widget(
            cancel_button
        )

        layout.add_widget(
            Label(
                text="Dosya adı:"
            )
        )

        layout.add_widget(
            name
        )

        layout.add_widget(
            buttons
        )

        popup = Popup(
            title="Farklı Kaydet",
            content=layout,
            size_hint=(0.9, 0.35)
        )

        def save(*args):

            filename = name.text.strip()

            if not filename:
                return

            if not filename.endswith(".py"):
                filename += ".py"

            directory = Path(
                App.get_running_app().user_data_dir
            )

            path = directory / filename

            try:

                path.write_text(
                    self.editor.text,
                    encoding="utf-8"
                )

                self.current_file = str(path)

                self.filename_label.text = filename

                self.status.text = (
                    "Kaydedildi: "
                    + filename
                )

                popup.dismiss()

            except Exception as e:

                self.output_text(
                    "\nKaydetme hatası:\n"
                    + str(e)
                    + "\n"
                )

        save_button.bind(
            on_release=save
        )

        cancel_button.bind(
            on_release=popup.dismiss
        )

        popup.open()

    # -------------------------------------------------
    # OPEN
    # -------------------------------------------------

    def open_file(self, *args):

        layout = BoxLayout(
            orientation="vertical",
            spacing=5
        )

        chooser = FileChooserListView(
            path=App.get_running_app().user_data_dir,
            filters=["*.py", "*.*"]
        )

        buttons = BoxLayout(
            size_hint_y=None,
            height=45,
            spacing=5
        )

        open_button = Button(
            text="Aç"
        )

        cancel_button = Button(
            text="İptal"
        )

        buttons.add_widget(
            open_button
        )

        buttons.add_widget(
            cancel_button
        )

        layout.add_widget(
            chooser
        )

        layout.add_widget(
            buttons
        )

        popup = Popup(
            title="Python dosyası aç",
            content=layout,
            size_hint=(0.95, 0.9)
        )

        def open_selected(*args):

            if not chooser.selection:
                return

            path = chooser.selection[0]

            try:

                self.editor.text = Path(
                    path
                ).read_text(
                    encoding="utf-8"
                )

                self.current_file = path

                self.filename_label.text = (
                    Path(path).name
                )

                self.status.text = (
                    "Açıldı: "
                    + Path(path).name
                )

                popup.dismiss()

            except Exception as e:

                self.output_text(
                    "\nAçma hatası:\n"
                    + str(e)
                    + "\n"
                )

        open_button.bind(
            on_release=open_selected
        )

        cancel_button.bind(
            on_release=popup.dismiss
        )

        popup.open()

    # -------------------------------------------------
    # RUN
    # -------------------------------------------------

    def run_code(self, *args):

        if self.running:
            return

        code = self.editor.text

        self.running = True

        self.status.text = "Çalışıyor..."

        self.output_text(
            "\n>>> Çalıştırılıyor...\n"
        )

        thread = threading.Thread(
            target=self.execute_code,
            args=(code,),
            daemon=True
        )

        thread.start()

    # -------------------------------------------------
    # EXECUTE
    # -------------------------------------------------

    def execute_code(self, code):

        stdout = io.StringIO()
        stderr = io.StringIO()

        original_input = builtins.input

        def mobile_input(prompt=""):

            self.output_text(
                str(prompt)
            )

            event = threading.Event()

            result = {
                "value": ""
            }

            def receive(value):

                result["value"] = value

                event.set()

            def activate(dt):

                self.input_box.callback = receive

                self.input_box.focus = True

            Clock.schedule_once(
                activate
            )

            event.wait()

            self.output_text(
                result["value"] + "\n"
            )

            return result["value"]

        namespace = {
            "__name__": "__main__",
            "__file__": self.current_file or "main.py"
        }

        try:

            builtins.input = mobile_input

            with redirect_stdout(stdout), redirect_stderr(stderr):

                compiled = compile(
                    code,
                    self.current_file or "main.py",
                    "exec"
                )

                exec(
                    compiled,
                    namespace,
                    namespace
                )

            result = stdout.getvalue()

            errors = stderr.getvalue()

            if result:
                self.output_text(result)

            if errors:
                self.output_text(errors)

            self.output_text(
                "\n>>> Program bitti.\n"
            )

            self.set_status(
                "Hazır"
            )

        except Exception:

            self.output_text(
                "\n"
                + traceback.format_exc()
                + "\n"
            )

            self.set_status(
                "Hata oluştu"
            )

        finally:

            builtins.input = original_input

            self.running = False

            Clock.schedule_once(
                lambda dt:
                setattr(
                    self.input_box,
                    "callback",
                    None
                )
            )

    # -------------------------------------------------
    # STOP
    # -------------------------------------------------

    def stop_code(self, *args):

        if not self.running:
            return

        self.output_text(
            "\n>>> Durdurma istendi.\n"
        )

        self.status.text = (
            "Durdurma istendi"
        )

        self.input_box.callback = (
            lambda value: None
        )

    # -------------------------------------------------
    # CLEAR
    # -------------------------------------------------

    def clear_output(self, *args):

        self.output.text = ""

        self.status.text = "Hazır"

    # -------------------------------------------------
    # STATUS
    # -------------------------------------------------

    def set_status(self, text):

        Clock.schedule_once(
            lambda dt:
            setattr(
                self.status,
                "text",
                text
            )
        )


class PythonPocket(App):

    def build(self):

        self.title = "PythonPocket IDE"

        Path(
            self.user_data_dir
        ).mkdir(
            parents=True,
            exist_ok=True
        )

        return PythonIDE()


if __name__ == "__main__":

    PythonPocket().run()
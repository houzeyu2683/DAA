from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog


class ChatApp(App):
    CSS = """
    RichLog {
        height: 1fr;
        border: solid green;
    }
    Input {
        dock: bottom;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(wrap=True, highlight=True, markup=True)
        yield Input(placeholder="輸入訊息...")
        yield Footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.value.strip().lower() == "exit":
            self.exit()
            return

        log = self.query_one(RichLog)
        log.write(f"你: {event.value}")
        event.input.value = ""


if __name__ == "__main__":
    ChatApp().run()

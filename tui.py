from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog, Static

from main_reAct import agent, config


class ChatTerminal(App):

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(wrap=True, highlight=True, markup=True)
        yield Input(placeholder="...")
        yield Footer()

    def on_mount(self) -> None:
        self.theme = "tokyo-night"

    async def on_input_submitted(self, event: Input.Submitted) -> None:

        if event.value.strip().lower() == "exit":
            self.exit()
            return

        log = self.query_one(RichLog)
        # streaming = self.query_one("#streaming", Static)
        user_input = event.value
        log.write(f"你: {user_input}")
        event.input.value = ""

        response_content = ""
        async for chunk, metadata in agent.astream(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
            stream_mode="messages",
        ):
            if chunk.type == "ai" and chunk.content:
                response_content += chunk.content
                # streaming.update(f"Agent: {response_content}")

        log.write(f"Agent: {response_content}")
        # streaming.update("")


if __name__ == "__main__":
    ChatTerminal().run()

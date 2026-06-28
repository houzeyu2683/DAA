from db.connection import get_connection


class Session:
    def __init__(self, db_path: str):
        self.con = get_connection(db_path)
        self.views: dict[str, str] = {}
        self.messages: list = []

    def build_context(self) -> str:
        if not self.views:
            return "目前 session 中沒有已儲存的 view。"
        lines = ["目前 session 中已有以下 view 可直接使用："]
        for name, desc in self.views.items():
            lines.append(f"  - {name}：{desc}")
        return "\n".join(lines)

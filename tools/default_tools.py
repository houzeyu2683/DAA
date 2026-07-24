import os
import io
import webbrowser
import contextlib
from dotenv import load_dotenv
from collections import Counter
from urllib.parse import quote
import duckdb as db
from pathlib import Path
from typing import Literal, Optional
from langchain.tools import tool
from langgraph.types import interrupt
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import itertools


@tool
def is_file_exist(file_path: str) -> bool:
    """
    檢查檔案是否存在。
    """

    return os.path.isfile(file_path)


@tool
def create_database(database_path: str) -> bool:
    """
    新增一個資料庫。
    """

    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    con = db.connect(database_path)
    con.close()
    return True


@tool
def is_table_exist(database_path: str, table_name: str) -> bool:
    """檢查資料庫中的資料表是否存在"""

    con = db.connect(database_path, read_only=True)
    try:
        exists = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table_name],
        ).fetchone()[0] > 0
    finally:
        con.close()
    return exists


@tool
def create_table(database_path: str, table_name: str, table_path: str) -> bool:
    """
    新增一張資料表。
    """

    con = db.connect(database_path)
    try:
        con.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM read_csv_auto(?)",
            [table_path],
        )
    finally:
        con.close()
    return True


@tool
def show_column_names(database_path: str, table_name: str) -> dict:
    """顯示資料表中的欄位名稱，欄位太多會縮減方式呈現。"""

    con = db.connect(database_path, read_only=True)
    rows = con.execute(f"DESCRIBE {table_name}").fetchall()
    con.close()
    all_column_names = [row[0] for row in rows]
    total = len(all_column_names)
    if total > 12:
        head_column_names = all_column_names[ :6]
        tail_column_names = all_column_names[-6:]
        head_content = ','.join(head_column_names)
        tail_content = ','.join(tail_column_names)
        return {
            'column_names': head_content + '......' + tail_content,
            'column_total': total
        }
    return {
        'column_names': ','.join(all_column_names),
        'column_total': total
    }



@tool
def is_columns_exist(database_path: str, table_name: str, column_names: list) -> dict:
    """
    檢查欄位是否存在於資料表中。

    範例：{'user_id': True, 'user_name': False}
    """

    con = db.connect(database_path, read_only=True)
    try:
        existing_columns = {
            row[0] for row in con.execute(f"DESCRIBE {table_name}").fetchall()
        }
    finally:
        con.close()
    return {name: name in existing_columns for name in column_names}


@tool
def search_column_type_distribution_with_pattern(database_path: str, table_name: str, column_pattern: str, pattern_mode: Literal['equals', 'contains', 'starts', 'ends']) -> dict:
    """
    依照欄位名稱的比對模式，回傳符合條件欄位的資料型別分佈。

    pattern_mode 可以是：
        - equals：欄位名稱與 column_pattern 完全相符
        - contains：欄位名稱包含 column_pattern
        - starts：欄位名稱開頭是 column_pattern
        - ends：欄位名稱結尾是 column_pattern
    """

    con = db.connect(database_path, read_only=True)
    try:
        schema = con.execute(f"DESCRIBE {table_name}").fetchall()
    finally:
        con.close()

    matched_types = []
    for col_name, col_type in schema:
        if pattern_mode == "equals" and col_name == column_pattern:
            matched_types.append(col_type)
        elif pattern_mode == "contains" and column_pattern in col_name:
            matched_types.append(col_type)
        elif pattern_mode == "starts" and col_name.startswith(column_pattern):
            matched_types.append(col_type)
        elif pattern_mode == "ends" and col_name.endswith(column_pattern):
            matched_types.append(col_type)

    return dict(Counter(matched_types))


@tool
def select_columns_from_table(database_path: str, table_name: str, column_names: list, checkpoint_name: str) -> dict:
    """查詢指定欄位，並將查詢結果另存為一個檢查點（checkpoint）表格。"""

    con = db.connect(database_path)
    try:
        columns_clause = ", ".join(column_names)
        con.execute(
            f"CREATE OR REPLACE TABLE {checkpoint_name} AS SELECT {columns_clause} FROM {table_name}"
        )
        row_count = con.execute(f"SELECT COUNT(*) FROM {checkpoint_name}").fetchone()[0]
    finally:
        con.close()
    return {
        "checkpoint_name": checkpoint_name,
        "row_count": row_count,
        "column_count": len(column_names),
    }


@tool
def preview_table(database_path: str, table_name: str) -> str:
    """預覽資料表內容。"""

    con = db.connect(database_path, read_only=True)
    try:
        rows_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        df = con.execute(f"SELECT * FROM {table_name}").fetchdf()
        columns_count = df.shape[1]
    finally:
        con.close()
    table_content = df.to_string(max_rows=6, max_cols=6, show_dimensions=False)
    table_preview = f'{table_content}\n\n{rows_count}x{columns_count}'
    return table_preview



@tool
def export_table(database_path: str, table_name: str, table_path: str) -> bool:
    """將資料表從資料庫匯出成檔案。"""

    Path(table_path).parent.mkdir(parents=True, exist_ok=True)
    con = db.connect(database_path, read_only=True)
    try:
        con.execute(
            f"COPY (SELECT * FROM {table_name}) TO ? (FORMAT CSV, HEADER)",
            [table_path],
        )
    finally:
        con.close()
    return True


@tool
def show_image(image_path: str) -> bool:
    """從指定路徑打開圖片，用預設瀏覽器開啟。"""

    if not os.path.isfile(image_path):
        return False

    uri = Path(image_path).resolve().as_uri()
    webbrowser.open(uri)
    return True


@tool
def send_email(to_user: str, subject: str, body: str, attachment_path: Optional[list] = None) -> bool:
    """寄送一封 email，attachment_path 可省略，省略就是純文字信件，不附加檔案。"""

    load_dotenv()
    msg = MIMEMultipart()
    msg["From"] = os.getenv("GOOGLE_EMAIL_ADDRESS")
    msg["To"] = to_user
    msg["Subject"] = subject
    msg.attach(MIMEText(body))

    if attachment_path:
        for path in attachment_path:
            with open(path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(path)}",
            )
            msg.attach(part)

    decision = interrupt({
        "question": "確認要寄出這封信嗎？請輸入 yes 確認，其他任何輸入視為取消。",
        "to": to_user,
        "subject": subject,
        "body": body,
        "attachments": [os.path.basename(p) for p in (attachment_path or [])],
    })

    if str(decision).strip().lower() != "yes":
        return False

    server = smtplib.SMTP("smtp.gmail.com", 587)
    try:
        server.starttls()
        server.login(os.getenv("GOOGLE_EMAIL_ADDRESS"), os.getenv("GOOGLE_EMAIL_TOKEN"))
        server.send_message(msg)
    finally:
        server.quit()
    return True


@tool
def read_file(file_path: str, offset_line: int = 0, limit_number: int = 2000) -> str:
    """讀取檔案內容，每行前面附上行號，方便之後用行號定位。
    可用 offset（從第幾行開始，0 為檔案開頭）與 limit（讀取行數，預設 2000）分頁讀取大檔案。
    """

    with open(file_path, "r", encoding="utf-8") as f:
        selected = list(itertools.islice(f, offset_line, offset_line + limit_number))
    file_lines = enumerate(selected, start=offset_line + 1)
    content = [f"{i}\t{line.rstrip(chr(10))}" for i, line in file_lines]
    return "\n".join(content)


import os
import re
import base64
import mimetypes
from typing import Literal
from pathlib import Path
import itertools
from langchain.tools import tool

def is_file_exist(file_path: str) -> bool:
    """檢查檔案是否存在。"""

    return os.path.isfile(file_path)


def is_folder_exist(folder_path: str) -> bool:
    """檢查資料夾是否存在。"""

    return os.path.isdir(folder_path)


def list_files(folder_path: str, offset_index: int = 0, limit_number: int = 20) -> dict:
    """瀏覽資料夾底下的檔案，為了避免過長，預設指定一個索引範圍。"""

    all_paths = Path(folder_path).iterdir()
    all_file_names = [path.name for path in all_paths if path.is_file()]
    all_file_total = len(all_file_names)
    limit_index = offset_index + limit_number
    file_names = all_file_names[offset_index: limit_index]
    return {
        'all_file_total': all_file_total,
        'offset_index': offset_index,
        'limit_number': limit_number,
        'file_names': file_names
    }


def list_folders(folder_path: str, offset_index: int = 0, limit_number: int = 20) -> dict:
    """瀏覽資料夾底下的資料夾，為了避免過長，預設指定一個索引範圍。"""

    all_paths = Path(folder_path).iterdir()
    all_folder_names = [path.name for path in all_paths if path.is_dir()]
    all_folder_total = len(all_folder_names)
    limit_index = offset_index + limit_number
    folder_names = all_folder_names[offset_index: limit_index]
    return {
        'all_folder_total': all_folder_total,
        'offset_index': offset_index,
        'limit_number': limit_number,
        'folder_names': folder_names
    }


def search_files(folder_path: str, file_name: str, offset_index: int = 0, limit_number: int = 20) -> dict:
    """在指定資料夾底下遞歸的尋找某些檔案，為了避免過長，預設指定一個索引範圍。"""

    all_matched_paths = Path(folder_path).rglob(file_name)
    all_matched_file_names = [
        path.name for path in all_matched_paths if path.is_file()
    ]

    all_matched_file_total = len(all_matched_file_names)
    limit_index = offset_index + limit_number
    matched_file_names = all_matched_file_names[offset_index: limit_index]
    return {
        'all_matched_file_total': all_matched_file_total,
        'offset_index': offset_index,
        'limit_number': limit_number,
        'matched_file_names': matched_file_names
    }



def search_files_with_regular_expression(folder_path: str, regular_expression: str, offset_index: int = 0, limit_number: int = 20) -> dict:
    """在指定資料夾底下遞歸的使用正規語法尋找某些檔案，為了避免過長，預設指定一個索引範圍。"""

    all_paths = Path(folder_path).rglob('*')
    pattern_syntax = re.compile(regular_expression)
    all_matched_file_names = [
        str(path) for path in all_paths 
        if path.is_file() and pattern_syntax.search(path.name)
    ]
    all_matched_file_total = len(all_matched_file_names)
    limit_index = offset_index + limit_number
    matched_file_names = all_matched_file_names[offset_index: limit_index]
    return {
        'all_matched_file_total': all_matched_file_total,
        'offset_index': offset_index,
        'limit_number': limit_number,
        'matched_file_names': matched_file_names
    }



def read_file(file_path: str, offset_index: int = 0, limit_number: int = 20) -> dict:
    """讀取檔案內容，為了避免過長，預設指定一個索引範圍。"""

    limit_index = offset_index + limit_number
    with open(file_path, "r", encoding="utf-8") as all_content:
        select_content = itertools.islice(
            all_content, 
            offset_index, 
            limit_index
        )
        select_lines = list(select_content)
    line_iteration = enumerate(select_lines, start=offset_index + 1)
    content_lines = [
        f"{index}\t{content.rstrip(chr(10))}" 
        for index, content in line_iteration
    ]
    file_content = "\n".join(content_lines)
    return {
        "file_content": file_content,
        "offset_index": offset_index,
        "limit_number": limit_number   
    }




def create_folder(folder_path: str) -> dict:
    """建立資料夾，如果已存在則不會報錯，並回報建立前是否已存在。"""

    folder_already_exist = os.path.isdir(folder_path)
    Path(folder_path).mkdir(parents=True, exist_ok=True)

    return {
        'folder_path': folder_path,
        'folder_already_exist': folder_already_exist
    }


def create_file(file_path: str) -> dict:
    """建立空白檔案，如果已存在則不會覆蓋內容，並回報建立前是否已存在。"""

    file_already_exist = os.path.isfile(file_path)
    Path(file_path).touch(exist_ok=True)

    return {
        'file_path': file_path,
        'file_already_exist': file_already_exist
    }


def write_content_in_file(file_path: str, content_character: str, write_mode: Literal["append", "overwrite"] = 'append') -> dict:
    """將指定內容寫入檔案，write_mode 可選擇 append(附加在檔案末端)或 overwrite(覆蓋整份檔案)。"""

    file_mode = 'a' if write_mode == 'append' else 'w'
    with open(file_path, file_mode, encoding="utf-8") as file_paper:
        file_paper.write(content_character)
    written_character_total = len(content_character)

    return {
        'file_path': file_path,
        'write_mode': write_mode,
        'written_character_total': written_character_total
    }


def view_image(image_path: str) -> list:
    """讀取圖片檔案，以多模態內容格式回傳，讓有視覺能力的模型可以直接看到圖片內容並進行解讀。"""

    mime_type, _ = mimetypes.guess_type(image_path)
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

    return [
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type or 'image/png'};base64,{encoded_image}"
            },
        }
    ]


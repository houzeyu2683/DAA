def search_code_in_file(file_path: str, code_content: str, offset_index: int = 0, limit_number: int = 20) -> dict:
    """在指定檔案中搜尋含有某段文字的行，依照字面精確比對，為了避免過長，預設指定一個索引範圍。"""

    all_matched_line_numbers = []
    with open(file_path, "r", encoding="utf-8") as all_file_content:
        all_content_iteration = enumerate(all_file_content, start=1)
        for line_number, line_content in all_content_iteration:
            if code_content not in line_content:
                continue
            all_matched_line_numbers.append(line_number)
            continue
        all_matched_line_total = len(all_matched_line_numbers)

    limit_index = offset_index + limit_number
    matched_line_numbers = all_matched_line_numbers[
        offset_index: limit_index
    ]
    return {
        'all_matched_line_total': all_matched_line_total,
        'offset_index': offset_index,
        'limit_number': limit_number,
        'matched_line_numbers': matched_line_numbers
    }
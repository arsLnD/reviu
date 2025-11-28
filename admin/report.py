# admin/report.py
from datetime import datetime
from io import BytesIO
from openpyxl import Workbook
from db_manager.db import Database

def generate_report(db: Database):
    """
    Генерирует XLSX-отчёт по таблице feedback и возвращает:
    (BytesIO объект с файлом, имя файла, текстовое резюме)
    Без столбца user_id
    """
    feedbacks = db.get_all_feedbacks()  # [(id, user_id, description, status), ...]
    users = db.get_all_users()

    wb = Workbook()
    ws = wb.active
    ws.title = "feedbacks"

    # Заголовки без user_id
    headers = ["id", "status", "description"]
    ws.append(headers)

    # Заполняем строки (пропускаем user_id)
    for fid, user_id, description, status in feedbacks:
        ws.append([fid, status, description or ""])

    # Подгоняем ширину колонок
    for column_cells in ws.columns:
        length = max((len(str(cell.value)) if cell.value is not None else 0) for cell in column_cells)
        col_letter = column_cells[0].column_letter
        ws.column_dimensions[col_letter].width = min(max(length + 2, 10), 100)

    # Сохраняем в BytesIO
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    # Имя файла
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"feedback_report_{now_str}.xlsx"

    # Резюме
    total_users = len(users)
    total_feedbacks = len(feedbacks)
    open_count = sum(1 for _, _, _, status in feedbacks if status == 0)
    closed_count = total_feedbacks - open_count

    summary_lines = [
        f"Отчёт: {now_str}",
        f"Пользователи в БД: {total_users}",
        f"Всего заявок: {total_feedbacks}",
        f"Открытых: {open_count}",
        f"Закрытых: {closed_count}",
    ]
    summary = "\n".join(summary_lines)

    return bio, filename, summary
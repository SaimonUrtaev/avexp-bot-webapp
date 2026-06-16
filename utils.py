"""
Общие утилиты для бота и облачной функции.
Убирает дублирование кода между bot.py и cloud_function/index.py
"""


def _safe(val):
    """Безопасное получение значения или прочерк."""
    return (val or "—").strip() or "—"


def get_headers_list():
    """Список всех колонок таблицы Google Sheets."""
    return [
        "№",
        "ПАРК",
        "МАРКА ТС",
        "ГОС.НОМЕР",
        "ГОД ТС",
        "ПОЛИС ОСАГО",
        "ДАТА ДТП",
        "ДАТА ПОДАЧИ",
        "ДАТА ОСМОТРА",
        "№ УБЫТКА",
        "СК",
        "ЛИЗИНГ",
        "ВЫРАБОТКА",
        "ЗАДАЧА НА",
        "УТС",
        "СУММА",
        "КАЛЬКУЛЯЦИЯ",
        "НАМ 15%",
        "СТАТУС ОПЛАТЫ",
        "ПРИМЕЧАНИЕ",
        "ГОРОД",
        "ГИБДД",
        "ГДЕ АДМИНКА",
        "ПРИВЕЗ АДМИНКУ",
        "ОСМОТР ПОД НЭ",
        "ВИНОВНИКИ ДТП",
        "УСЛОВИЯ",
    ]


def build_text(number: int, data: dict, photo_count: int = 0) -> str:
    """Построить текст уведомления с данными убытка."""
    admin_note = data.get("admin_note", "").strip()
    text = (
        f"✅ *Убыток №{number} записан!*\n\n"
        f"🏢 ПАРК: `{_safe(data.get('park')).upper()}`\n"
        f"🚗 МАРКА ТС: `{_safe(data.get('brand')).upper()}`\n"
        f"🔢 ГОС.НОМЕР: `{_safe(data.get('grz')).upper()}`\n"
        f"📄 ПОЛИС ОСАГО: `{_safe(data.get('policy')).upper()}`\n"
        f"📅 ДАТА ДТП: `{_safe(data.get('date_dtp'))}`\n"
        f"🏦 СК: `{_safe(data.get('insurance')).upper()}`\n"
    )
    if admin_note:
        text += f"📝 АДМИН МАТЕРИАЛ: `{admin_note}`\n"
    if photo_count > 0:
        text += f"📎 Фото: {photo_count} шт."
    return text

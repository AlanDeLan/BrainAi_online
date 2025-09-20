import os
import sys
import datetime
import json
from fastapi import APIRouter, Request
from core.logic import process_with_archetype, load_archetypes

try:
    from vector_db.client import save_chat
except ImportError:
    save_chat = None

# --- Функція для коректної роботи з ресурсами у PyInstaller ---
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

router = APIRouter()
archetypes_dict = load_archetypes()

ARCHETYPES_ORDER = ["sofiya", "lyra", "maker"]

HISTORY_DIR = resource_path("history")
os.makedirs(HISTORY_DIR, exist_ok=True)

@router.post("/conference/rada")
async def conference_rada(request: Request):
    data = await request.json()
    text = data.get("text")
    selected = data.get("archetypes", ARCHETYPES_ORDER)
    remember = data.get("remember", True)

    # 1. Початкові відповіді
    initial = {}
    for archetype in selected:
        result = process_with_archetype(text, archetype, archetypes_dict)
        initial[archetype] = result.get("response", result.get("error", ""))

    # 2. Дискусія
    discussion = {}
    lyra_prompt = (
        f"Софія запропонувала ідею:\n{initial.get('sofiya', '')}\n\n"
        "Як критик і матеріаліст, проаналізуй цю ідею, вкажи на її сильні та слабкі сторони."
    )
    lyra_result = process_with_archetype(lyra_prompt, "lyra", archetypes_dict)
    discussion["lyra"] = lyra_result.get("response", lyra_result.get("error", ""))

    maker_prompt = (
        f"Софія запропонувала ідею:\n{initial.get('sofiya', '')}\n\n"
        f"Ліра прокоментувала так:\n{discussion['lyra']}\n\n"
        "Як технолог і виконавець, запропонуй практичне рішення або план дій, враховуючи ідею та критику."
    )
    maker_result = process_with_archetype(maker_prompt, "maker", archetypes_dict)
    discussion["maker"] = maker_result.get("response", maker_result.get("error", ""))

    sofiya_prompt = (
        f"Твоя початкова ідея:\n{initial.get('sofiya', '')}\n\n"
        f"Ліра прокоментувала:\n{discussion['lyra']}\n\n"
        f"Мейкер запропонував:\n{discussion['maker']}\n\n"
        "Як креативний генератор, підсумуй дискусію і запропонуй фінальний творчий висновок."
    )
    sofiya_result = process_with_archetype(sofiya_prompt, "sofiya", archetypes_dict)
    discussion["sofiya"] = sofiya_result.get("response", sofiya_result.get("error", ""))

    consensus_prompt = (
        "Ось підсумок обговорення між учасниками Ради:\n"
        f"Софія (генератор): {initial.get('sofiya', '')}\n\n"
        f"Ліра (критик): {discussion['lyra']}\n\n"
        f"Мейкер (технолог): {discussion['maker']}\n\n"
        f"Софія (підсумок): {discussion['sofiya']}\n\n"
        "Сформулюй спільну відповідь/консенсус від імені всієї Ради, коротко і по суті."
    )
    consensus_result = process_with_archetype(consensus_prompt, "lyra", archetypes_dict)
    consensus = consensus_result.get("response", consensus_result.get("error", ""))

    # --- Зберігаємо всю конференцію одним файлом ---
    if remember:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join(HISTORY_DIR, f"{timestamp}_rada.json")
        rada_data = {
            "timestamp": timestamp,
            "type": "rada",
            "user_input": text,
            "archetypes": selected,
            "initial": initial,
            "discussion": discussion,
            "consensus": consensus
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(rada_data, f, ensure_ascii=False, indent=4)
        # Зберігаємо у векторну базу як один документ
        if save_chat:
            chat_id = f"rada_{timestamp}"
            chat_text = (
                f"Питання: {text}\n\n"
                f"Початкові відповіді:\n"
                f"Софія: {initial.get('sofiya', '')}\n"
                f"Ліра: {initial.get('lyra', '')}\n"
                f"Мейкер: {initial.get('maker', '')}\n\n"
                f"Обговорення:\n"
                f"Ліра: {discussion.get('lyra', '')}\n"
                f"Мейкер: {discussion.get('maker', '')}\n"
                f"Софія: {discussion.get('sofiya', '')}\n\n"
                f"Консенсус: {consensus}"
            )
            save_chat(
                chat_id=chat_id,
                chat_text=chat_text,
                archetypes=selected,
                timestamp=timestamp,
                topic=None
            )

    return {
        "initial": {
            "sofiya": initial.get("sofiya", ""),
            "lyra": initial.get("lyra", ""),
            "maker": initial.get("maker", "")
        },
        "discussion": {
            "lyra": discussion.get("lyra", ""),
            "maker": discussion.get("maker", ""),
            "sofiya": discussion.get("sofiya", "")
        },
        "consensus": consensus,
    }
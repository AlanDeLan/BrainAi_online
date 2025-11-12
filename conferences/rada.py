import os
import sys
import datetime
import json
from fastapi import APIRouter, Request, HTTPException
from core.logic import process_with_archetype, load_archetypes
from core.utils import get_base_dir

try:
    from vector_db.client import save_chat
except ImportError:
    save_chat = None

router = APIRouter()

HISTORY_DIR = os.path.join(get_base_dir(), "history")
os.makedirs(HISTORY_DIR, exist_ok=True)

def get_archetype_info(archetype_name, archetypes_dict):
    """Отримує інформацію про архетип з конфігурації."""
    archetype_config = archetypes_dict.get(archetype_name, {})
    return {
        "name": archetype_config.get("name", archetype_name),
        "description": archetype_config.get("description", ""),
        "role": archetype_config.get("role", "")
    }

def build_discussion_prompt(archetype_name, archetype_info, initial_responses, all_archetypes_info, user_question):
    """Побудова промпту для обговорення на основі ролі агента."""
    role = archetype_info.get("role", "")
    name = archetype_info.get("name", archetype_name)
    
    # Формуємо контекст з початкових відповідей інших агентів
    context_parts = []
    for arch_name, arch_info in all_archetypes_info.items():
        if arch_name != archetype_name and arch_name in initial_responses:
            context_parts.append(f"{arch_info['name']} ({arch_info['description']}):\n{initial_responses[arch_name]}")
    
    context = "\n\n".join(context_parts)
    
    # Формуємо промпт залежно від ролі
    if role == "critic":
        prompt = f"""Питання користувача: {user_question}

Ось початкові відповіді інших учасників Ради:

{context}

Як критичний аналітик, проаналізуй ці ідеї, вкажи на їх сильні та слабкі сторони, вияви потенційні ризики та недоліки. Будь конструктивним у своїй критиці."""
    
    elif role == "executor":
        prompt = f"""Питання користувача: {user_question}

Ось ідеї та думки інших учасників Ради:

{context}

Як практичний виконавець, запропонуй конкретний план дій або практичне рішення, враховуючи всі обговорені ідеї. Сфокусуйся на реальній реалізації."""
    
    elif role == "creative_generator":
        prompt = f"""Питання користувача: {user_question}

Твоя початкова відповідь:
{initial_responses.get(archetype_name, '')}

Ось початкові відповіді інших учасників Ради:

{context}

Як творчий генератор, проаналізуй ці ідеї та дай свою думку, враховуючи різні підходи та перспективи."""
    
    else:
        # Загальний промпт для інших ролей
        prompt = f"""Питання користувача: {user_question}

Ось початкові відповіді інших учасників Ради:

{context}

Дай свою думку та внесок у обговорення, враховуючи все вищесказане."""
    
    return prompt

@router.post("/conference/rada")
async def conference_rada(request: Request):
    """
    Режим РАДА: обговорення питання між агентами (до 3 агентів).
    Агенти обираються з конфігурації archetypes.yaml.
    """
    data = await request.json()
    text = data.get("text")
    selected_archetypes = data.get("archetypes", [])
    remember = data.get("remember", True)
    
    if not text:
        raise HTTPException(status_code=400, detail="Question is required")
    
    # Load archetypes
    archetypes_dict = load_archetypes()
    
    # If no agents specified, take all available (maximum 3)
    if not selected_archetypes or len(selected_archetypes) == 0:
        selected_archetypes = list(archetypes_dict.keys())[:3]
        if len(selected_archetypes) == 0:
            raise HTTPException(
                status_code=400, 
                detail="No agents found in configuration"
            )
    
    # Limit to 3 agents
    if len(selected_archetypes) > 3:
        selected_archetypes = selected_archetypes[:3]
    
    # Minimum 1 agent
    if len(selected_archetypes) < 1:
        raise HTTPException(
            status_code=400, 
            detail="At least one agent must be selected for RADA mode"
        )
    
    # Check agent availability
    for arch_name in selected_archetypes:
        if arch_name not in archetypes_dict:
            raise HTTPException(
                status_code=400, 
                detail=f"Agent '{arch_name}' not found in configuration"
            )
    
    # Отримуємо інформацію про агентів
    archetypes_info = {
        arch_name: get_archetype_info(arch_name, archetypes_dict)
        for arch_name in selected_archetypes
    }
    
    # 1. Початкові відповіді від усіх агентів
    initial = {}
    for archetype in selected_archetypes:
        result = process_with_archetype(text, archetype, archetypes_dict)
        initial[archetype] = result.get("response", result.get("error", ""))
    
    # 2. Обговорення: кожен агент коментує початкові відповіді інших
    discussion = {}
    for archetype in selected_archetypes:
        archetype_info = archetypes_info[archetype]
        discussion_prompt = build_discussion_prompt(
            archetype, 
            archetype_info, 
            initial, 
            archetypes_info,
            text
        )
        result = process_with_archetype(discussion_prompt, archetype, archetypes_dict)
        discussion[archetype] = result.get("response", result.get("error", ""))
    
    # 3. Формування консенсусу
    # Вибираємо агента для формування консенсусу (пріоритет: critic > executor > creative_generator)
    consensus_archetype = None
    for role_priority in ["critic", "executor", "creative_generator"]:
        for arch_name, arch_info in archetypes_info.items():
            if arch_info.get("role") == role_priority:
                consensus_archetype = arch_name
                break
        if consensus_archetype:
            break
    
    # Якщо не знайшли за роллю, беремо першого
    if not consensus_archetype:
        consensus_archetype = selected_archetypes[0]
    
    # Формуємо промпт для консенсусу
    consensus_context = []
    for arch_name in selected_archetypes:
        arch_info = archetypes_info[arch_name]
        consensus_context.append(
            f"{arch_info['name']} ({arch_info['description']}) - Початкова думка:\n{initial.get(arch_name, '')}\n\n"
            f"Під час обговорення:\n{discussion.get(arch_name, '')}"
        )
    
    consensus_prompt = f"""Питання користувача: {text}

Ось підсумок обговорення між учасниками Ради:

{chr(10).join(consensus_context)}

Сформулюй спільну відповідь/консенсус від імені всієї Ради. Відповідь має бути короткою, збалансованою та враховувати всі думки учасників."""
    
    consensus_result = process_with_archetype(consensus_prompt, consensus_archetype, archetypes_dict)
    consensus = consensus_result.get("response", consensus_result.get("error", ""))
    
    # --- Зберігаємо всю конференцію ---
    if remember:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join(HISTORY_DIR, f"{timestamp}_rada.json")
        
        # Створюємо маппінг ключів до назв для зручності перегляду історії
        archetype_names_map = {
            arch_name: archetypes_info[arch_name]['name'] 
            for arch_name in selected_archetypes
        }
        
        # Конвертуємо initial та discussion на назви агентів
        initial_with_names = {
            archetype_names_map.get(arch_name, arch_name): response
            for arch_name, response in initial.items()
        }
        discussion_with_names = {
            archetype_names_map.get(arch_name, arch_name): response
            for arch_name, response in discussion.items()
        }
        
        rada_data = {
            "timestamp": timestamp,
            "type": "rada",
            "user_input": text,
            "archetypes": selected_archetypes,
            "archetype_names": archetype_names_map,  # Додаємо маппінг для зручності
            "initial": initial_with_names,  # Зберігаємо з назвами
            "discussion": discussion_with_names,  # Зберігаємо з назвами
            "consensus": consensus
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(rada_data, f, ensure_ascii=False, indent=4)
        
        # Зберігаємо у векторну базу
        if save_chat:
            chat_id = f"rada_{timestamp}"
            chat_text_parts = [f"Питання: {text}\n\nПочаткові відповіді:"]
            for arch_name in selected_archetypes:
                arch_info = archetypes_info[arch_name]
                chat_text_parts.append(f"{arch_info['name']}: {initial.get(arch_name, '')}")
            chat_text_parts.append("\nОбговорення:")
            for arch_name in selected_archetypes:
                arch_info = archetypes_info[arch_name]
                chat_text_parts.append(f"{arch_info['name']}: {discussion.get(arch_name, '')}")
            chat_text_parts.append(f"\nКонсенсус: {consensus}")
            chat_text = "\n".join(chat_text_parts)
            
            save_chat(
                chat_id=chat_id,
                chat_text=chat_text,
                archetypes=selected_archetypes,
                timestamp=timestamp,
                topic=None
            )
    
    # Формуємо відповідь з назвами агентів
    response_initial = {}
    response_discussion = {}
    
    for arch_name in selected_archetypes:
        arch_info = archetypes_info[arch_name]
        display_name = arch_info['name']
        response_initial[display_name] = initial.get(arch_name, "")
        response_discussion[display_name] = discussion.get(arch_name, "")
    
    return {
        "initial": response_initial,
        "discussion": response_discussion,
        "consensus": consensus,
        "archetypes_used": [archetypes_info[arch]['name'] for arch in selected_archetypes]
    }
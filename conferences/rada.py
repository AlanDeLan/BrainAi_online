from fastapi import APIRouter
from core.logic import process_with_archetype, load_archetypes

router = APIRouter()
archetypes_dict = load_archetypes()

ARCHETYPES_ORDER = ["sofiya", "lyra", "maker"]  # Софія – генератор, Ліра – критик, Мейкер – технолог

@router.post("/conference/rada")
async def conference_rada(data: dict):
    text = data.get("text")
    selected = data.get("archetypes", ARCHETYPES_ORDER)
    # 1. Початкові відповіді
    initial = {}
    for archetype in selected:
        result = process_with_archetype(text, archetype, archetypes_dict)
        initial[archetype] = result.get("response", result.get("error", ""))

    # 2. Дискусія (1 ітерація)
    discussion = {}
    # Софія генерує ідеї, Ліра критикує, Мейкер пропонує рішення
    # Ліра бачить ідею Софії, Мейкер бачить ідею Софії та критику Ліри
    # Софія може прокоментувати підсумок

    # Ліра (критик) аналізує ідею Софії
    lyra_prompt = (
        f"Софія запропонувала ідею:\n{initial.get('sofiya', '')}\n\n"
        "Як критик і матеріаліст, проаналізуй цю ідею, вкажи на її сильні та слабкі сторони."
    )
    lyra_result = process_with_archetype(lyra_prompt, "lyra", archetypes_dict)
    discussion["lyra"] = lyra_result.get("response", lyra_result.get("error", ""))

    # Мейкер (технолог) бачить ідею Софії та критику Ліри
    maker_prompt = (
        f"Софія запропонувала ідею:\n{initial.get('sofiya', '')}\n\n"
        f"Ліра прокоментувала так:\n{discussion['lyra']}\n\n"
        "Як технолог і виконавець, запропонуй практичне рішення або план дій, враховуючи ідею та критику."
    )
    maker_result = process_with_archetype(maker_prompt, "maker", archetypes_dict)
    discussion["maker"] = maker_result.get("response", maker_result.get("error", ""))

    # Софія може підсумувати дискусію (опційно)
    sofiya_prompt = (
        f"Твоя початкова ідея:\n{initial.get('sofiya', '')}\n\n"
        f"Ліра прокоментувала:\n{discussion['lyra']}\n\n"
        f"Мейкер запропонував:\n{discussion['maker']}\n\n"
        "Як креативний генератор, підсумуй дискусію і запропонуй фінальний творчий висновок."
    )
    sofiya_result = process_with_archetype(sofiya_prompt, "sofiya", archetypes_dict)
    discussion["sofiya"] = sofiya_result.get("response", sofiya_result.get("error", ""))

    # 3. Консенсус (підсумок від імені всієї Ради)
    consensus_prompt = (
        "Ось підсумок обговорення між учасниками Ради:\n"
        f"Софія (генератор): {initial.get('sofiya', '')}\n\n"
        f"Ліра (критик): {discussion['lyra']}\n\n"
        f"Мейкер (технолог): {discussion['maker']}\n\n"
        f"Софія (підсумок): {discussion['sofiya']}\n\n"
        "Сформулюй спільну відповідь/консенсус від імені всієї Ради, коротко і по суті."
    )
    consensus_result = process_with_archetype(consensus_prompt, "lyra", archetypes_dict)

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
        "consensus": consensus_result.get("response", consensus_result.get("error", "")),
    }
import json

def debug_logger(agent_name: str, state: dict, msg: str = ""):
    print(f"\n🧠 [DEBUG] Agente: {agent_name}")
    if msg:
        print(f"📌 {msg}")
    print(f"📦 Estado parcial:")
    print(json.dumps(state, indent=2, ensure_ascii=False))
from utils.schemas import State

def human_interrupt(state: State) -> State:
    """Handle cases where human input is needed"""
    return state
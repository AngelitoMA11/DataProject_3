from typing import Annotated, List, Literal
from typing_extensions import TypedDict 
from langgraph.graph.message import add_messages
from langgraph.prebuilt.chat_agent_executor import AgentState


# class CustomAgentState(AgentState):
#     """The state of the agent."""
#     # messages: Annotated[Sequence[BaseMessage], add_messages]
#     # is_last_step: IsLastStep
#     # remaining_steps: RemainingSteps

#     # TODO Añadir estados para los agentes


from typing import TypedDict, Optional, Dict, Any, List

# Estado del viaje
class ViajeState(TypedDict, total=False):
    mensaje_usuario: str
    destino: Optional[str]
    fechas: Optional[Dict[str, str]]
    preferencias: Dict[str, Any]
    vuelo_elegido: Optional[Dict[str, Any]]
    alojamiento_elegido: Optional[Dict[str, Any]]
    presupuesto_inicial: Optional[float]
    presupuesto_restante: Optional[float]
    siguiente_agente: Optional[str]
    contexto_user: Optional[Dict[str, Any]]
    destino_determinado: Optional[bool]
    campos_faltantes: Optional[List[Dict[str, str]]]
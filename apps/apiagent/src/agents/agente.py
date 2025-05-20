# agente.py

import datetime
import operator
import os
from typing import Annotated, TypedDict, List, Optional

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver # Asegúrate que memorysaver esté configurado para estos campos
from langgraph.graph import END, StateGraph
import traceback

# --- IMPORTAR HERRAMIENTAS ---
from src.tools.itinerario import comprehensive_itinerary_generator_tool as real_itinerary_tool
from src.tools.vuelos import flights_finder
from src.tools.hoteles import hotels_finder
from src.tools.donde import destination_explorer_tool, initialize_destination_explorer


CURRENT_YEAR = datetime.datetime.now().year

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    destination: Optional[str]
    departure_date: Optional[str]
    arrival_date: Optional[str]
    intereses: Optional[str]
    flight_info_gathered: bool
    hotel_info_gathered: bool
    itinerary_generated: bool
    last_flight_info: Optional[str]
    last_hotel_info: Optional[str]
    # Nuevos campos para el explorador de destinos
    explorer_conversation_history: Optional[List[dict]]
    explorer_is_finished: bool


TOOLS_SYSTEM_PROMPT = f"""You are a smart travel agency. Use the tools to look up information.
    You are allowed to make multiple calls (either together or in sequence).
    Only look up information when you are sure of what you want.
    The current year is {CURRENT_YEAR}. Your knowledge cutoff is before this year, so always verify critical changing information like opening hours or specific events.
    If you need to look up some information before asking a follow up question, you are allowed to do that!
    I want to have in your output links to hotels websites and flights websites (if possible).
    I want to have as well the logo of the hotel and the logo of the airline company (if possible).
    In your output always include the price of the flight and the price of the hotel and the currency as well (if possible).
    for example for hotels-
    Rate: $581 per night
    Total: $3,488

    Tool Usage Guide:

    1. 'destination_explorer_tool':
        - Use this tool if the user is unsure about their destination city or wants help choosing one.
        - To call this tool, you primarily need to provide the user's current relevant query or statement as the 'user_input' argument. For example: {{"user_input": "I'd like to go somewhere sunny in Europe."}}
        - The tool will automatically use its ongoing conversation history, which is managed by the system. You DO NOT need to explicitly pass the full conversation history in the tool arguments unless you are an advanced system trying to override it.
        - The tool will conduct a conversation to help the user pick a specific city.
        - It will return a response for the user. The 'destination' and 'intereses' in the main agent state will be updated IF the tool finalizes a city.
        - If the tool indicates it's not finished (check 'explorer_is_finished' in the main agent state, which will be 'False'), its response is for the user. Await the user's next input, and if it's related to choosing a destination, call 'destination_explorer_tool' again with the new 'user_input'.
        - When 'destination_explorer_tool' finalizes (explorer_is_finished in the main agent state becomes 'True' and a destination is confirmed):
            - The tool's response (delivered via the ToolMessage) will typically be a confirmation and a natural transition question (e.g., "Great, we've chosen Paris! Shall we look for flights now?").
            - Your subsequent response to the user should acknowledge this and directly address the user's next request based on this transition.
            - Do NOT repeat a summary like "Destino Elegido: [Ciudad], Intereses: [Intereses]" back to the user, as the tool has already handled the confirmation conversationally. Simply use the confirmed city and interests from the main agent state for the next planning step.
        - Only use other tools (flights_finder, etc.) AFTER 'destination_explorer_tool' has confirmed a city (i.e., 'destination' is set in the main agent state and 'explorer_is_finished' is True).


    2. 'flights_finder':
        - Use AFTER a destination city is known (i.e., 'destination' is set in the main agent state).
        - Requires: {{"ciudad_origen": "XYZ", "ciudad_destino": "ABC", "fecha_salida": "YYYY-MM-DD", "fecha_vuelta": "YYYY-MM-DD", "adults": N}}
        - This tool will update flight_info_gathered and potentially destination/dates in the main state.

    3. 'hotels_finder':
        - Use AFTER a destination city is known.
        - Requires: {{"ciudad": "City", "fecha_entrada": "YYYY-MM-DD", "fecha_vuelta": "YYYY-MM-DD", "adults": N}}
        - This tool will update hotel_info_gathered and potentially ciudad/dates in the main state.

    4. 'comprehensive_itinerary_generator_tool':
        - Use this to generate a travel itinerary ONLY AFTER ciudad, departure_date, arrival_date, and interests are known and confirmed in the main state.
        - Requires: {{"ciudad": "City, Country", "departure_date": "DD de mes de YYYY", "arrival_date": "DD de mes de YYYY", "intereses": "e.g., museums, local food"}}
        - This tool performs its own web research if needed.

    General Flow:
    - If the main agent state shows 'destination' is None or the user expresses uncertainty about the destination, your first step should be to call 'destination_explorer_tool' with the user's input.
    - If 'destination_explorer_tool' was used and the main agent state shows 'explorer_is_finished' is 'False':
        - Your primary action for the next turn (if the user continues the destination discussion) should be to call 'destination_explorer_tool' again.
        - Provide the new 'user_input' from the user. The tool will handle its own conversation history internally.
    - Once 'destination_explorer_tool' finalizes (main agent state 'explorer_is_finished' is 'True' and 'destination' is set), the user will likely respond to the tool's transition question. Your job is to take that user response and call the next appropriate tool (flights, hotels, itinerary) or answer directly.
    """

# --- LISTA DE HERRAMIENTAS ---
TOOLS = [flights_finder, hotels_finder, real_itinerary_tool, destination_explorer_tool]

class Agent:
    def __init__(self, tools: list):
        self._tools = {t.name: t for t in tools}
        self.itinerary_tool_name = real_itinerary_tool.name
        self.explorer_tool_name = destination_explorer_tool.name # Nombre de la nueva herramienta

        try:
            self._tools_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2).bind_tools(tools) # Adjusted temperature
            print("Orchestrator LLM (gemini-1.5-flash) initialized and tools bound.")
        except Exception as e:
            print(f"ERROR initializing orchestrator LLM: {e}")
            raise

        builder = StateGraph(AgentState)
        builder.add_node('call_tools_llm', self.call_tools_llm)
        builder.add_node('invoke_tools', self.invoke_tools_and_update_state)
        builder.add_node('generate_itinerary_node', self.invoke_specific_itinerary_tool)

        builder.set_entry_point('call_tools_llm')

        builder.add_conditional_edges(
            'call_tools_llm',
            self.should_invoke_tools,
            { 'invoke': 'invoke_tools', 'end': END }
        )
        
        builder.add_conditional_edges(
            'invoke_tools',
            self.should_generate_itinerary_or_continue,
            {
                'generate_itinerary': 'generate_itinerary_node',
                'continue_to_llm': 'call_tools_llm',
                'end': END
            }
        )
        
        builder.add_edge('generate_itinerary_node', 'call_tools_llm')

        memory = MemorySaver()
        self.graph = builder.compile(checkpointer=memory)
        print("Orchestrator agent graph compiled.")

    @staticmethod
    def should_invoke_tools(state: AgentState):
        print("  [Router should_invoke_tools]")
        if not state['messages'] or not isinstance(state['messages'][-1], AIMessage):
            print("    Last message not AIMessage or no messages, ending.")
            return 'end'
        last_message = state['messages'][-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls and len(last_message.tool_calls) > 0:
            print(f"    LLM requested {len(last_message.tool_calls)} tool(s). Proceeding to invoke_tools.")
            return 'invoke'
        print("    No tool calls from LLM. Ending.")
        return 'end'

    def call_tools_llm(self, state: AgentState):
        messages = state['messages']
        # Crear una copia del estado para mostrar, excluyendo objetos no serializables si es necesario
        current_state_snapshot = {k: v for k, v in state.items() if k != 'messages'}
        
        print(f"  [Orchestrator call_tools_llm] Current state snapshot: {current_state_snapshot}")

        final_messages_for_llm = [SystemMessage(content=TOOLS_SYSTEM_PROMPT)] + messages
        
        
        print(f"  [Orchestrator call_tools_llm] Calling LLM with {len(final_messages_for_llm)} messages.")
        if messages: print(f"    Last message to LLM: {type(messages[-1])} Content: {str(messages[-1].content)[:100]}...")
        
        ai_message = self._tools_llm.invoke(final_messages_for_llm)
        print(f"    LLM Response (AIMessage): tool_calls={ai_message.tool_calls}, content='{str(ai_message.content)[:100]}...'")
        return {'messages': [ai_message]}


    def invoke_tools_and_update_state(self, state: AgentState):
        print("  [Node invoke_tools_and_update_state]")
        if not state['messages'] or not isinstance(state['messages'][-1], AIMessage) or not state['messages'][-1].tool_calls:
            print("    [ERROR] Expected AIMessage with tool_calls as last message.")
            return {"messages": [ToolMessage(content="Error: Estado inconsistente, no se encontraron tool_calls.", tool_call_id="error_state_no_tool_calls")]}

        tool_calls = state['messages'][-1].tool_calls
        results = []
        updated_state_values = {} # Para acumular cambios al estado

        for t_call in tool_calls:
            tool_name = t_call['name']
            tool_args_from_llm = t_call['args']
            print(f"    Calling: {tool_name} with raw args from LLM: {tool_args_from_llm}")

            if tool_name not in self._tools:
                print(f"      [ERROR] Bad tool name: '{tool_name}'. Available: {list(self._tools.keys())}")
                result_content = f"Error: Tool '{tool_name}' no encontrada."
            else:
                try:
                    params_to_invoke_tool_with = tool_args_from_llm
                    params_for_state_update = tool_args_from_llm # Por defecto

                    if tool_name == flights_finder.name or tool_name == hotels_finder.name:
                        # Estas herramientas esperan {'params': {...}}
                        # params_to_invoke_tool_with ya es tool_args_from_llm (que debería ser {'params': ...})
                        if "params" in tool_args_from_llm:
                            params_for_state_update = tool_args_from_llm.get("params", {})
                        else:
                            print(f"      [WARNING] LLM args for {tool_name} did not contain 'params' key. Args: {tool_args_from_llm}")
                            # La herramienta fallará si su schema espera 'params'
                            
                    elif tool_name == self.explorer_tool_name:
                        # La herramienta explorador espera 'user_input' y opcionalmente 'current_explorer_state_messages'
                        # El LLM debería idealmente pasar {'user_input': '...'}
                        user_input_for_explorer = tool_args_from_llm.get("user_input", "")
                        if not user_input_for_explorer and state.get("messages"): # Intento de fallback
                            for msg in reversed(state["messages"]):
                                if isinstance(msg, HumanMessage):
                                    user_input_for_explorer = msg.content
                                    print(f"      [INFO] Explorer tool called without 'user_input' arg, using last HumanMessage: '{user_input_for_explorer[:50]}...'")
                                    break
                        
                        params_to_invoke_tool_with = {
                            "user_input": user_input_for_explorer,
                            "current_explorer_state_messages": state.get("explorer_conversation_history")
                        }
                        # params_for_state_update no es directamente aplicable aquí, el resultado de la herramienta lo dictará

                    # Invocar la herramienta
                    result = self._tools[tool_name].invoke(params_to_invoke_tool_with)
                    
                    # Procesar resultado y actualizar estado
                    if tool_name == self.explorer_tool_name:
                        # El resultado es un dict: {"explorer_response": ..., "updated_explorer_messages_history": ..., "is_finished": ..., "final_data": ...}
                        result_content = result.get("explorer_response", "El explorador de destinos no proporcionó respuesta.")
                        updated_state_values["explorer_conversation_history"] = result.get("updated_explorer_messages_history")
                        updated_state_values["explorer_is_finished"] = result.get("is_finished", False)
                        print(f"      Explorer tool: finished={updated_state_values['explorer_is_finished']}, response='{result_content[:100]}...'")

                        if updated_state_values["explorer_is_finished"]:
                            final_data = result.get("final_data")
                            if final_data and final_data.get("Destino Elegido"):
                                updated_state_values["destination"] = final_data["Destino Elegido"]
                                updated_state_values["intereses"] = final_data.get("intereses", state.get("intereses")) # Mantener intereses si ya existen
                                print(f"      Explorer tool finalized. Destination: '{updated_state_values['destination']}', Intereses: '{updated_state_values.get('intereses')}'")
                                # Podríamos resetear el historial si ya no se necesita
                                # updated_state_values["explorer_conversation_history"] = None 
                            else:
                                print("      [WARNING] Explorer tool finished but no valid final_data for destination.")
                    else:
                        result_content = str(result) # Para otras herramientas

                    if tool_name == flights_finder.name:
                        updated_state_values["flight_info_gathered"] = True
                        updated_state_values["last_flight_info"] = result_content
                        if not state.get("destination") and params_for_state_update.get("arrival_airport"):
                            updated_state_values["destination"] = params_for_state_update["arrival_airport"]
                        if not state.get("departure_date") and params_for_state_update.get("outbound_date"):
                            updated_state_values["departure_date"] = params_for_state_update["outbound_date"]
                        if not state.get("arrival_date") and params_for_state_update.get("return_date"):
                            updated_state_values["arrival_date"] = params_for_state_update["return_date"]
                        print(f"      Set flight_info_gathered=True, updated related state: { {k:v for k,v in updated_state_values.items() if k in ['destination','departure_date','arrival_date']} }")

                    elif tool_name == hotels_finder.name:
                        updated_state_values["hotel_info_gathered"] = True
                        updated_state_values["last_hotel_info"] = result_content
                        if not state.get("destination") and params_for_state_update.get("destination"):
                            updated_state_values["destination"] = params_for_state_update["destination"]
                        if not state.get("departure_date") and params_for_state_update.get("checkin_date"):
                             updated_state_values["departure_date"] = params_for_state_update["checkin_date"]
                        if not state.get("arrival_date") and params_for_state_update.get("checkout_date"):
                             updated_state_values["arrival_date"] = params_for_state_update["checkout_date"]
                        print(f"      Set hotel_info_gathered=True, updated related state: { {k:v for k,v in updated_state_values.items() if k in ['destination','departure_date','arrival_date']} }")
                    
                    elif tool_name == self.itinerary_tool_name:
                        updated_state_values["itinerary_generated"] = True
                        itinerary_args_used = params_for_state_update # Args directos
                        for key_param in ["destination", "departure_date", "arrival_date", "intereses"]:
                            if key_param in itinerary_args_used and itinerary_args_used[key_param]:
                                if not updated_state_values.get(key_param) or \
                                   (state.get(key_param) != itinerary_args_used[key_param] and updated_state_values.get(key_param) != itinerary_args_used[key_param]):
                                    updated_state_values[key_param] = itinerary_args_used[key_param]
                        print(f"      LLM called itinerary tool. Set itinerary_generated=True. Updated state: { {k:v for k,v in updated_state_values.items() if k in ['destination','departure_date','arrival_date', 'intereses']} }")
                        
                except Exception as e:
                    print(f"      [ERROR] Error invoking tool {tool_name}: {e}")
                    traceback.print_exc()
                    result_content = f"Error al ejecutar la herramienta {tool_name}: {str(e)}"
            
            results.append(ToolMessage(tool_call_id=t_call['id'], name=tool_name, content=result_content))
        
        print(f"    Tools invoked. Results ({len(results)}) sent back.")
        # Devolver los mensajes de herramienta y los cambios acumulados al estado
        final_return = {"messages": results}
        if updated_state_values:
            final_return.update(updated_state_values)
        return final_return

    def should_generate_itinerary_or_continue(self, state: AgentState):
        print("  [Router should_generate_itinerary_or_continue]")
        
        # Verificar si el explorador de destinos está activo y no ha terminado
        if not state.get("explorer_is_finished", True) and state.get("explorer_conversation_history") is not None:
            print("    Explorer tool is active and not finished. Continuing to LLM to get user's next input for explorer.")
            return 'continue_to_llm' # El LLM principal debería entonces llamar al explorador de nuevo.

        causing_ai_message = None
        if len(state['messages']) >= 2:
            num_tool_messages_at_end = 0
            for msg in reversed(state['messages']):
                if isinstance(msg, ToolMessage): num_tool_messages_at_end += 1
                else: break
            if len(state['messages']) > num_tool_messages_at_end:
                potential_ai_msg_idx = -1 - num_tool_messages_at_end
                if isinstance(state['messages'][potential_ai_msg_idx], AIMessage):
                    causing_ai_message = state['messages'][potential_ai_msg_idx]

        flight_gathered = state.get("flight_info_gathered", False)
        hotel_gathered = state.get("hotel_info_gathered", False)
        itinerary_already_generated = state.get("itinerary_generated", False)
        
        destination = state.get("destination")
        departure_date = state.get("departure_date")
        arrival_date = state.get("arrival_date")
        intereses = state.get("intereses")

        print(f"    Checking conditions: flight_gathered={flight_gathered}, hotel_gathered={hotel_gathered}, itinerary_generated={itinerary_already_generated}")
        print(f"    Params for itinerary from state: dest={destination}, dep_date={departure_date}, arr_date={arrival_date}, interests={intereses}")

        if causing_ai_message and causing_ai_message.tool_calls:
            if any(tc['name'] == self.itinerary_tool_name for tc in causing_ai_message.tool_calls):
                print("    Itinerary tool was just explicitly called by LLM. No auto-trigger. Continuing to LLM.")
                return 'continue_to_llm'

        if flight_gathered and hotel_gathered and not itinerary_already_generated:
            if destination and departure_date and arrival_date and intereses:
                print("    Conditions met for automatic itinerary generation. Routing to generate_itinerary_node.")
                return 'generate_itinerary'
            else:
                print("    Flights/Hotels gathered, but missing dest, dates, or interests for auto-itinerary. Continuing to LLM.")
                return 'continue_to_llm'
        
        print("    Conditions for auto-itinerary not met or itinerary already generated. Continuing to LLM.")
        return 'continue_to_llm'

    def invoke_specific_itinerary_tool(self, state: AgentState):
        print("  [Node invoke_specific_itinerary_tool] (Auto-triggered Itinerary)")
        destination = state.get("destination")
        departure_date = state.get("departure_date")
        arrival_date = state.get("arrival_date")
        intereses = state.get("intereses")
        last_flight_info = state.get("last_flight_info", "No flight details available.")
        last_hotel_info = state.get("last_hotel_info", "No hotel details available.")

        if not (destination and departure_date and arrival_date and intereses):
            error_msg = "Error: (Auto-Itinerary) Missing essential parameters (destination, dates, or interests) from state."
            print(f"    {error_msg} - State: dest={destination}, dep_date={departure_date}, arr_date={arrival_date}, interests={intereses}")
            return {"messages": [ToolMessage(content=error_msg, name=self.itinerary_tool_name, tool_call_id="error_auto_itinerary_params")]}

        tool_args = { "destination": destination, "departure_date": departure_date, "arrival_date": arrival_date, "intereses": intereses, "flight_details": last_flight_info, "hotel_details": last_hotel_info }
        print(f"    Calling {self.itinerary_tool_name} with auto-gathered args: {tool_args}")
        
        try:
            result = self._tools[self.itinerary_tool_name].invoke(tool_args)
            result_content = str(result)
            tool_call_id = f"auto_itinerary_call_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            tool_message = ToolMessage(tool_call_id=tool_call_id, name=self.itinerary_tool_name, content=result_content)
            updated_state_values = {"itinerary_generated": True, "messages": [tool_message]}
            print(f"    {self.itinerary_tool_name} invoked successfully by system. Itinerary generated.")
            return updated_state_values
        except Exception as e:
            print(f"      [ERROR] Error auto-invoking {self.itinerary_tool_name}: {e}")
            traceback.print_exc()
            result_content = f"Error al auto-ejecutar {self.itinerary_tool_name}: {str(e)}"
            tool_call_id = f"error_auto_itinerary_exec_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            return {"messages": [ToolMessage(tool_call_id=tool_call_id, name=self.itinerary_tool_name, content=result_content)]}


travel_agent = Agent(tools=TOOLS)
import datetime
import operator
import os
from typing import Annotated, TypedDict, List, Optional

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
import traceback

from src.tools.itinerario import comprehensive_itinerary_generator_tool as real_itinerary_tool
from src.tools.vuelos import flights_finder
from src.tools.hoteles import hotels_finder
from src.tools.donde import destination_explorer_tool, initialize_destination_explorer
from src.tools.itinerario_simple import itinerary_planner_tool


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
    explorer_conversation_history: Optional[List[dict]]
    explorer_is_finished: bool


TOOLS_SYSTEM_PROMPT = f"""You are a smart travel agency. Use the tools to look up information.
    You are allowed to make multiple calls (either together or in sequence).
    Only look up information when you are sure of what you want.
    Today is 21th of May of 2025. Your knowledge cutoff is before this year, so always verify critical changing information like opening hours or specific events.
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
        - If you don't have the departure city, you can use the user's last input or the last known city as 'ciudad_origen'. If not available, you can ask the user for it.
        - The default value for 'ciudad_origen' is "VLC" if the user doesn't say it. 
        - Always put the IATA code of the international airport in the ciudad_destino, so the LLM can use it in the response.
        - If there isn't an international airport in the city, you can use the nearest one. (e.g., "REP" for Battambang)

    3. 'hotels_finder':
        - Use AFTER a destination city is known.
        - Requires: {{"ciudad": "City", "fecha_entrada": "YYYY-MM-DD", "fecha_vuelta": "YYYY-MM-DD", "adults": N}}
        - This tool will update hotel_info_gathered and potentially ciudad/dates in the main state.
        - Always put the images url in markdown format, so the LLM can use it in the response.

    4. 'itinerary_planner_tool':
        - Use this tool to generate a simple itinerary once the destination and dates are confirmed.
        - Call this tool when the user asks for a itinerary.
        - Expected arguments (example): {{"ciudad": "CityName", "departure_date": "YYYY-MM-DD", "arrival_date": "YYYY-MM-DD", "intereses": "e.g., sightseeing, food"}}
       (The LLM should adapt based on the tool's actual schema if it differs, but provide these common fields if available from conversation).
        After presenting the simple itinerary to the user, ask explicitly if you are satisfied or if you want a more detailed plan or with different suggestions. If yes, use the 'comprehensive_itinerary_generator_tool' to generate a more detailed itinerary.

    5. 'comprehensive_itinerary_generator_tool': 
        - When to use: ONLY AFTER you have used itinerary_planner_tool and the user has indicated that you want a more detailed, different itinerary or are not satisfied with the simple itinerary provided.
        - Use this tool to generate a **detailed and comprehensive** travel itinerary, potentially including day-by-day plans, activity suggestions, and researched information.
        - This tool is also used by the system for **automatic itinerary generation** if flight and hotel details are confirmed and no specific itinerary type was requested by the user.
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
TOOLS = [flights_finder, hotels_finder, real_itinerary_tool, itinerary_planner_tool, destination_explorer_tool]

class Agent:
    def __init__(self, tools: list):
        self._tools = {t.name: t for t in tools}
        self.itinerary_tool_name = real_itinerary_tool.name
        self.simple_itinerary_tool_name = itinerary_planner_tool.name
        self.explorer_tool_name = destination_explorer_tool.name 

        try:
            self._tools_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-05-20", temperature=0.2).bind_tools(tools)
            print("Orchestrator LLM (gemini-2.5-flash-preview-05-20) initialized and tools bound.")
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
        updated_state_values = {} 

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
                    
                    if tool_name == flights_finder.name or tool_name == hotels_finder.name:
                        if "params" not in tool_args_from_llm:
                            print(f"      [WARNING] LLM args for {tool_name} did not contain 'params' key. Args: {tool_args_from_llm}. Tool might fail if it expects 'params'.")
                        # Tool invocation will proceed with tool_args_from_llm; it might fail if structure is wrong.
                        # params_for_state_update will use tool_args_from_llm.get("params", {}) later if needed
                            
                    elif tool_name == self.explorer_tool_name:
                        user_input_for_explorer = tool_args_from_llm.get("user_input", "")
                        if not user_input_for_explorer and state.get("messages"):
                            for msg in reversed(state["messages"]):
                                if isinstance(msg, HumanMessage):
                                    user_input_for_explorer = msg.content
                                    print(f"      [INFO] Explorer tool called without 'user_input' arg, using last HumanMessage: '{user_input_for_explorer[:50]}...'")
                                    break
                        
                        params_to_invoke_tool_with = {
                            "user_input": user_input_for_explorer,
                            "current_explorer_state_messages": state.get("explorer_conversation_history")
                        }

                    result = self._tools[tool_name].invoke(params_to_invoke_tool_with)
                    
                    # --- Process result and update state ---
                    params_for_state_update = tool_args_from_llm
                    if tool_name == flights_finder.name or tool_name == hotels_finder.name:
                        if "params" in tool_args_from_llm:
                             params_for_state_update = tool_args_from_llm.get("params", {})
                        # else: params_for_state_update remains tool_args_from_llm, state update might be less effective

                    if tool_name == self.explorer_tool_name:
                        result_content = result.get("explorer_response", "El explorador de destinos no proporcionó respuesta.")
                        updated_state_values["explorer_conversation_history"] = result.get("updated_explorer_messages_history")
                        explorer_is_finished_from_tool = result.get("is_finished", False)
                        updated_state_values["explorer_is_finished"] = explorer_is_finished_from_tool
                        print(f"      Explorer tool: finished={updated_state_values['explorer_is_finished']}, response='{str(result_content)[:100]}...'")

                        if explorer_is_finished_from_tool:
                            final_data = result.get("final_data")
                            if final_data and final_data.get("Destino Elegido"):
                                updated_state_values["destination"] = final_data["Destino Elegido"]
                                updated_state_values["intereses"] = final_data.get("intereses", state.get("intereses"))
                                print(f"      Explorer tool finalized. Destination: '{updated_state_values['destination']}', Intereses: '{updated_state_values.get('intereses')}'")
                            else:
                                print("      [WARNING] Explorer tool finished but no valid final_data for destination.")
                    else:
                        result_content = str(result)

                    if tool_name == flights_finder.name:
                        updated_state_values["flight_info_gathered"] = True
                        updated_state_values["last_flight_info"] = result_content
                        # Update state from params_for_state_update (which is tool_args_from_llm.get("params", {}))
                        if not state.get("destination") and params_for_state_update.get("ciudad_destino"):
                            updated_state_values["destination"] = params_for_state_update["ciudad_destino"]
                        if not state.get("departure_date") and params_for_state_update.get("fecha_salida"):
                            updated_state_values["departure_date"] = params_for_state_update["fecha_salida"]
                        if not state.get("arrival_date") and params_for_state_update.get("fecha_vuelta"):
                            updated_state_values["arrival_date"] = params_for_state_update["fecha_vuelta"]
                        print(f"      Set flight_info_gathered=True, updated related state: { {k:v for k,v in updated_state_values.items() if k in ['destination','departure_date','arrival_date']} }")

                    elif tool_name == hotels_finder.name:
                        updated_state_values["hotel_info_gathered"] = True
                        updated_state_values["last_hotel_info"] = result_content
                        # Update state from params_for_state_update (which is tool_args_from_llm.get("params", {}))
                        if not state.get("destination") and params_for_state_update.get("ciudad"):
                            updated_state_values["destination"] = params_for_state_update["ciudad"]
                        if not state.get("departure_date") and params_for_state_update.get("fecha_entrada"):
                             updated_state_values["departure_date"] = params_for_state_update["fecha_entrada"]
                        if not state.get("arrival_date") and params_for_state_update.get("fecha_vuelta"):
                             updated_state_values["arrival_date"] = params_for_state_update["fecha_vuelta"]
                        print(f"      Set hotel_info_gathered=True, updated related state: { {k:v for k,v in updated_state_values.items() if k in ['destination','departure_date','arrival_date']} }")
                    
                    elif tool_name == self.itinerary_tool_name or tool_name == self.simple_itinerary_tool_name:
                        updated_state_values["itinerary_generated"] = True
                        itinerary_args_used = tool_args_from_llm # LLM passes direct args for itinerary tools

                        param_mapping = [
                            ("destination", ["destination", "ciudad"]), 
                            ("departure_date", ["departure_date", "fecha_salida"]),
                            ("arrival_date", ["arrival_date", "fecha_vuelta", "fecha_llegada"]), # Added more flexible keys
                            ("intereses", ["intereses"])
                        ]

                        for state_key, llm_arg_keys in param_mapping:
                            for llm_arg_key in llm_arg_keys:
                                if llm_arg_key in itinerary_args_used and itinerary_args_used[llm_arg_key]:
                                    value_from_llm = itinerary_args_used[llm_arg_key]
                                    current_pending_update = updated_state_values.get(state_key)
                                    current_state_value = state.get(state_key)

                                    if current_pending_update is not None: 
                                        if current_pending_update != value_from_llm:
                                            updated_state_values[state_key] = value_from_llm 
                                    else: 
                                        if current_state_value is None or current_state_value != value_from_llm:
                                            updated_state_values[state_key] = value_from_llm
                                    break 
                        
                        tool_type_msg = "comprehensive" if tool_name == self.itinerary_tool_name else "simple"
                        print(f"      LLM called {tool_type_msg} itinerary tool ({tool_name}). Set itinerary_generated=True. Relevant state updates: { {k:v for k,v in updated_state_values.items() if k in ['destination','departure_date','arrival_date', 'intereses', 'itinerary_generated']} }")
                        
                except Exception as e:
                    print(f"      [ERROR] Error invoking tool {tool_name}: {e}")
                    traceback.print_exc()
                    result_content = f"Error al ejecutar la herramienta {tool_name}: {str(e)}"
            
            results.append(ToolMessage(tool_call_id=t_call['id'], name=tool_name, content=result_content))
        
        print(f"    Tools invoked. Results ({len(results)}) sent back.")
        final_return = {"messages": results}
        if updated_state_values:
            final_return.update(updated_state_values)
        return final_return

    def should_generate_itinerary_or_continue(self, state: AgentState):
        print("  [Router should_generate_itinerary_or_continue]")
        
        if not state.get("explorer_is_finished", True) and state.get("explorer_conversation_history") is not None:
            print("    Explorer tool is active and not finished. Continuing to LLM to get user's next input for explorer.")
            return 'continue_to_llm'

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
            explicitly_called_itinerary = False
            called_tool_name = ""
            for tc in causing_ai_message.tool_calls:
                if tc['name'] == self.itinerary_tool_name or tc['name'] == self.simple_itinerary_tool_name:
                    explicitly_called_itinerary = True
                    called_tool_name = tc['name']
                    break
            
            if explicitly_called_itinerary:
                print(f"    An itinerary tool ({called_tool_name}) was just explicitly called by LLM. No auto-trigger. Continuing to LLM.")
                return 'continue_to_llm'

        if flight_gathered and hotel_gathered and not itinerary_already_generated:
            if destination and departure_date and arrival_date and intereses:
                print("    Conditions met for automatic itinerary generation (comprehensive). Routing to generate_itinerary_node.")
                return 'generate_itinerary'
            else:
                missing_params = []
                if not destination: missing_params.append("destination")
                if not departure_date: missing_params.append("departure_date")
                if not arrival_date: missing_params.append("arrival_date")
                if not intereses: missing_params.append("intereses")
                print(f"    Flights/Hotels gathered, but missing {', '.join(missing_params)} for auto-itinerary. Continuing to LLM.")
                return 'continue_to_llm'
        
        print("Conditions for auto-itinerary not met or itinerary already generated. Continuing to LLM.")
        return 'continue_to_llm'

    def invoke_specific_itinerary_tool(self, state: AgentState):
        # This node automatically calls the COMPREHENSIVE itinerary tool
        print(f"  [Node invoke_specific_itinerary_tool] (Auto-triggered Itinerary - using {self.itinerary_tool_name})")
        destination = state.get("destination")
        departure_date = state.get("departure_date")
        arrival_date = state.get("arrival_date")
        intereses = state.get("intereses")
        last_flight_info = state.get("last_flight_info", "No flight details available.")
        last_hotel_info = state.get("last_hotel_info", "No hotel details available.")

        if not (destination and departure_date and arrival_date and intereses): # Ensure interests are present
            error_msg = "Error: (Auto-Itinerary) Missing essential parameters (destination, dates, or interests) from state for comprehensive itinerary."
            print(f"    {error_msg} - State: dest={destination}, dep_date={departure_date}, arr_date={arrival_date}, interests={intereses}")
            return {"messages": [ToolMessage(content=error_msg, name=self.itinerary_tool_name, tool_call_id="error_auto_itinerary_params")]}

        # Args for the comprehensive tool
        tool_args = { "ciudad": destination, "departure_date": departure_date, "arrival_date": arrival_date, "intereses": intereses, "flight_details": last_flight_info, "hotel_details": last_hotel_info }
        print(f"    Calling {self.itinerary_tool_name} with auto-gathered args: {tool_args}")
        
        try:
            # Using self.itinerary_tool_name which points to real_itinerary_tool (comprehensive)
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
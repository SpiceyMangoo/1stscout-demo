import pandas as pd
import json
import os
from typing import Tuple, Dict, Any, List

import plotly.graph_objects as go
import plotly.express as px

from openai import OpenAI
from langchain_core.utils.function_calling import convert_to_openai_function
from config.settings import OPENAI_API_KEY, ARCHETYPES_PATH, SYNONYM_LIBRARY_PATH, NLU_MAPPINGS_PATH
from insights.insight_engine import InsightEngine

from utils.logbook_handler import get_all_logbook_schemas


def _load_data() -> Tuple[dict, dict, dict]:
    """
    Loads all foundational knowledge assets (Archetypes, Synonyms, NLU Mappings) from disk at startup.
    """
    try:
        with open(ARCHETYPES_PATH, 'r') as f:
            archetypes = json.load(f)

        with open(SYNONYM_LIBRARY_PATH, 'r') as f:
            synonym_library = json.load(f)
        
        with open(NLU_MAPPINGS_PATH, 'r') as f:
            nlu_mappings = json.load(f)

        return archetypes, synonym_library, nlu_mappings
    except FileNotFoundError as e:
        raise RuntimeError(f"A required data file was not found. This is a fatal error. Please check your setup. Details: {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"A JSON knowledge file is corrupted. Please validate the file. Details: {e}")
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred while loading foundational knowledge files: {e}")

ARCHETYPES, SYNONYM_LIBRARY, NLU_MAPPINGS = _load_data()

ARCHETYPE_TO_POSITION_CATEGORY = {
    "Ball-Playing Defender": "Defender", "Stopper": "Defender", "Overlapping Full-Back": "Defender", "Inverted Full-Back": "Defender",
    "Anchor Man / Defensive Midfielder": "Midfielder", "Regista / Deep-Lying Playmaker": "Midfielder", "Box-to-Box Midfielder": "Midfielder",
    "Mezzala / Attacking 8": "Midfielder", "Advanced Playmaker / Number 10": "Midfielder",
    "Winger": "Forward", "Inside Forward": "Forward", "Pressing Forward": "Forward", "Target Man": "Forward",
    "Poacher / Goal Hanger": "Forward", "False Nine": "Forward",
    "Sweeper Keeper": "Goalkeeper", "Shot Stopper": "Goalkeeper"
}

POSITION_GROUPINGS = {
    'Forward': ['Striker', 'Attacking Midfielder', 'Winger', 'Pressing Forward'],
    'Midfielder': ['Attacking Midfielder', 'Defensive Midfielder', 'Center Midfielder'],
    'Defender': ['Center Back', 'Full Back'],
    'Goalkeeper': ['Goalkeeper']
}


def _calculate_fit_score(df: pd.DataFrame, normalization_context_df: pd.DataFrame, archetype_name: str) -> pd.Series:
    """Calculates a fit score for a given archetype and returns it as a Series."""
    if archetype_name not in ARCHETYPES:
        return None
    
    recipe = ARCHETYPES[archetype_name]['key_metrics']
    fit_score = pd.Series(0.0, index=df.index)
    
    for stat, weight in recipe.items():
        if stat in df.columns and pd.api.types.is_numeric_dtype(df[stat]):
            min_val = normalization_context_df[stat].min()
            max_val = normalization_context_df[stat].max()
            if (max_val - min_val) > 0:
                normalized_stat = (df[stat] - min_val) / (max_val - min_val)
                fit_score += normalized_stat.fillna(0) * weight
    return fit_score

def _internal_create_plot(df: pd.DataFrame, full_df: pd.DataFrame, x_axis: str, y_axis: str, title: str) -> go.Figure:
    """Creates a Plotly scatter plot with globally scaled axes."""
    for col in [x_axis, y_axis]:
        if col not in df.columns:
            raise ValueError(f"Error: Column '{col}' not found in the data for plotting. Current columns are: {df.columns.to_list()}")

    x_min_global = full_df[x_axis].min()
    x_max_global = full_df[x_axis].max()
    x_range_buffer = (x_max_global - x_min_global) * 0.05
    x_range = [x_min_global - x_range_buffer, x_max_global + x_range_buffer]

    y_min_global = full_df[y_axis].min()
    y_max_global = full_df[y_axis].max()
    y_range_buffer = (y_max_global - y_min_global) * 0.05
    y_range = [y_min_global - y_range_buffer, y_max_global + y_range_buffer]

    fig = px.scatter(
        df, x=x_axis, y=y_axis, title=title,
        hover_data=['full_name', 'age', 'primary_position'] + [c for c in df.columns if 'fit_score' in c],
        labels={x_axis: x_axis.replace('_', ' ').title(), y_axis: y_axis.replace('_', ' ').title()},
        template="plotly_white"
    )
    fig.update_layout(
        title_font_size=22,
        xaxis_title_font_size=16,
        yaxis_title_font_size=16,
        xaxis=dict(range=x_range),
        yaxis=dict(range=y_range)
    )
    fig.update_traces(marker=dict(size=12, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
    return fig

def _execute_search_and_filter(
    df: pd.DataFrame,
    normalization_context_df: pd.DataFrame,
    filters: List[Dict[str, Any]] = None,
    sort_by: str = None,
    sort_ascending: bool = True,
    add_archetype_as_column: str = None
) -> pd.DataFrame:
    """Internal logic to perform filtering and sorting on a given DataFrame."""
    working_df = df.copy()

    if add_archetype_as_column and add_archetype_as_column in ARCHETYPES:
        fit_score_col_name = f"fit_score_{add_archetype_as_column.lower().replace(' ', '_').replace('/', '_')}"
        working_df[fit_score_col_name] = _calculate_fit_score(working_df, normalization_context_df, add_archetype_as_column)
        print(f"DIAGNOSTIC: Added new fit score column '{fit_score_col_name}' for archetype '{add_archetype_as_column}'.")

    if filters:
        for f in filters:
            col = f.get("column")
            op = f.get("operator")
            val = f.get("value")

            if not all([col, op]) or val is None:
                print(f"DIAGNOSTIC: Skipping invalid filter: {f}")
                continue

            if col not in working_df.columns:
                print(f"DIAGNOSTIC: Skipping filter, column '{col}' not found.")
                continue

            try:
                if op == 'greater_than':
                    working_df = working_df[working_df[col] > float(val)]
                elif op == 'less_than':
                    working_df = working_df[working_df[col] < float(val)]
                elif op == 'equal_to':
                    working_df = working_df[working_df[col] == val]
                elif op == 'contains':
                    working_df = working_df[working_df[col].str.contains(val, case=False, na=False)]
                elif op == 'is_in':
                    working_df = working_df[working_df[col].isin(val)]
            except Exception as e:
                print(f"DIAGNOSTIC: Error applying filter {f}: {e}")

    if sort_by and sort_by in working_df.columns:
        working_df = working_df.sort_values(by=sort_by, ascending=sort_ascending)
    
    return working_df

def new_search(archetype_name: str, filters: List[Dict[str, Any]] = None) -> None:
    """Use this tool to start a completely new search from the entire dataset, anchored by a primary player archetype."""
    pass

def filter_and_sort(filters: List[Dict[str, Any]] = None, sort_by: str = None, sort_ascending: bool = True, add_archetype_as_column: str = None) -> None:
    """Use this tool to filter, sort, or add a new archetype context to the results of the MOST RECENT search."""
    pass

def create_plot(x_axis: str, y_axis: str, title: str) -> None:
    """Use this tool to create a plot of the players from the most recent search results."""
    pass

def add_log_entry(logbook_name: str, data: Dict[str, Any]) -> None:
    """
    Use this tool to add a new row of data to a specified custom logbook. You must provide the exact
    logbook_name from the <AVAILABLE_LOGBOOKS> context and a dictionary of data where keys are the exact
    column names. If a date is not specified by the user for a 'date' column, you MUST use today's date
    in 'YYYY-MM-DD' format.
    """
    # This function is a schema placeholder for the OpenAI tools integration.
    # The actual implementation is handled by `_internal_add_log_entry` to keep the tool
    # definition clean and separate from the execution logic.
    pass

def _internal_add_log_entry(current_logbooks: Dict[str, pd.DataFrame], logbook_name: str, data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """
    Internal implementation for adding an entry to a logbook DataFrame.
    This function is now pure and does not depend on session_state.
    """
    if logbook_name not in current_logbooks:
        raise ValueError(f"Logbook '{logbook_name}' not found.")

    logbook_df = current_logbooks[logbook_name]
    new_entry = {}
    for col in logbook_df.columns:
        new_entry[col] = data.get(col)
    new_row_df = pd.DataFrame([new_entry])
    updated_df = pd.concat([logbook_df, new_row_df], ignore_index=True)

    # Update the dictionary and return the entire updated collection
    current_logbooks[logbook_name] = updated_df
    print(f"DIAGNOSTIC: Successfully added entry to '{logbook_name}'. New shape: {updated_df.shape}")
    return current_logbooks
    
# --- SPRINT 3 NEW FEATURE: LOGBOOK Q&A TOOL ---
    # This is the placeholder schema for the agent.
    pass

class ScoutAgent:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model_name = "gpt-4.1-nano-2025-04-14"
        self.insight_engine = InsightEngine(archetypes=ARCHETYPES)

    # PASTE THE NEW METHOD HERE
    def _internal_query_logbook(self, logbook_name: str, question: str) -> str:
        """
        Internal implementation for querying a logbook DataFrame using an LLM for comprehension.
        """
        if 'logbooks' not in st.session_state or logbook_name not in st.session_state['logbooks']:
            return f"Error: The logbook '{logbook_name}' was not found in the current session."

        logbook_df = st.session_state['logbooks'][logbook_name]

        if logbook_df.empty:
            return f"The '{logbook_name}' logbook is currently empty."

        # Convert the DataFrame to a simple, clean Markdown string for the LLM.
        # This transforms the problem from "data analysis" to "reading comprehension".
        df_as_markdown = logbook_df.to_markdown(index=False)

        # Create a focused, lightweight prompt for the Q&A task.
        qa_prompt = f"""You are a data analysis assistant. Your sole task is to answer a user's question based ONLY on the data provided below.
        If the user asks to modify the data (e.g., "remove a row"), state that you cannot modify the data but provide the information they need to do it themselves.

        <data_context>
        {df_as_markdown}
        </data_context>

        Question: {question}

        Answer:"""

        try:
            # Use self.client and self.model_name, which are defined in __init__
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": qa_prompt}],
                temperature=0.0
            )
            answer = response.choices[0].message.content
            return answer
        except Exception as e:
            print(f"ERROR: Logbook Q&A LLM call failed: {e}")
            return "Sorry, I had a problem analyzing that logbook."
    
    def _classify_intent(self, query: str, chat_history: list) -> str:
        # ... (This method's logic is unchanged but remains part of the class) ...
        valid_archetypes = list(ARCHETYPES.keys())
        archetype_list_for_prompt = "\n".join(f"- '{name}'" for name in valid_archetypes)
        classifier_prompt = f"You are an intent classifier. Your only job is to determine if the user's request is for a 'new_search' or a 'refinement'.\n- A 'new_search' happens when the user explicitly mentions a player archetype, signalling they want to start over.\n- A 'refinement' happens when the user asks to filter, sort, plot, or add information to the players they are already looking at.\n\nValid Archetypes:\n{archetype_list_for_prompt}\n\nBased on the user's latest query, classify the intent as 'new_search' or 'refinement'. Your response MUST be one word: either 'new_search' or 'refinement'."
        messages = [{"role": "system", "content": classifier_prompt}] + chat_history + [{"role": "user", "content": query}]
        try:
            response = self.client.chat.completions.create(model="gpt-4.1-nano-2025-04-14", messages=messages, temperature=0, max_tokens=10)
            intent = response.choices[0].message.content.strip().lower()
            return 'refinement' if intent not in ['new_search', 'refinement'] else intent
        except Exception as e:
            print(f"DIAGNOSTIC: Intent classification failed: {e}")
            return 'refinement'

    def _generate_summary(self, query: str, function_name: str, function_args: Dict[str, Any]) -> str:
    """
    Generates a brief, friendly confirmation message after a tool call succeeds.
    This method is wrapped in its own error handling to prevent crashes.
    """
    summary_prompt = "You are an AI Football Scout. Your tool call was successful. Based on the original query and the tool called, write a brief, friendly confirmation message explaining what you did."
    messages = [
        {"role": "system", "content": summary_prompt},
        {"role": "user", "content": f"Query: {query}, Tool: {function_name}, Args: {json.dumps(function_args)}"}
    ]
    try:
        summary_response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages
        )
        return summary_response.choices[0].message.content
    except Exception as e:
        print(f"ERROR: Summary generation LLM call failed: {e}")
        # Provide a simple fallback message if the summary generation fails
        return f"Action '{function_name}' was completed successfully."

    def process_query(self, query: str, chat_history: list, full_df: pd.DataFrame, last_result_df: pd.DataFrame, active_archetype: str, current_logbooks: Dict[str, pd.DataFrame]) -> Dict[str, Any]:

        response = {}
        summary_text = ""
        
        # Initialize variables for the response at the beginning of the function.
        result_df = None
        plotly_fig = None
        display_df = None
        # Initialize as empty to act as a flag for the final summary logic.

        # --- DYNAMIC PROMPT ENGINEERING ---
        # Before every query, get the real-time schemas of all loaded custom logbooks.
        logbook_schemas = get_all_logbook_schemas(current_logbooks)
        
        # This block of text is dynamically generated. If no logbooks are loaded, it will be empty.
        logbook_context_prompt = ""
        if logbook_schemas:
            logbook_context_prompt = f"""<section name="AVAILABLE_LOGBOOKS">
     You have access to the following custom logbooks. When the user asks to log data, you MUST use the `add_log_entry` tool. When they ask a question about the data in a logbook, you MUST use the `query_logbook` tool.
     {logbook_schemas}
     </section>
     """

        valid_archetypes = list(ARCHETYPES.keys())
        archetype_list_for_prompt = "\n".join(f"- '{name}'" for name in valid_archetypes)
        column_list_for_prompt = json.dumps(list(full_df.columns)) if full_df is not None else "[]"

        # --- FINAL SYSTEM PROMPT ---
        # This version includes the full rule hierarchy for all tools.
        system_prompt = f"""You are an expert AI assistant and data entry specialist for a football scout. Your primary job is to translate natural language user requests into precise tool calls.

        {logbook_context_prompt}

        <rules>
     <rule name="Tool Choice Hierarchy - TOP PRIORITY">
     1.  First, check if the user is asking a question ABOUT a custom logbook (e.g., "who is in trials?", "what is player X's email?", "summarize the wellness log"). If so, you MUST use the `query_logbook` tool. The user's `question` for this tool should be their full, original query.
     2.  If it is not a question, check if the user wants to ADD data to a custom logbook (e.g., "log wellness data," "add RPE score"). If so, you MUST use the `add_log_entry` tool.
     3.  If the query is not related to custom logbooks, then proceed to the player search tools (`new_search`, `filter_and_sort`, `create_plot`).
     </rule>

        <rule name="CRITICAL: Log Entry Construction">
     - You MUST NOT call the `add_log_entry` tool unless the user's query provides BOTH a specific `logbook_name` AND the `data` to be logged.
     - The `logbook_name` MUST EXACTLY match one of the names provided in the `<AVAILABLE_LOGBOOKS>` schema.
     - The keys in the `data` dictionary MUST EXACTLY match the column names from that logbook's schema.
     - If a 'date' column exists and the user does not specify a date, you MUST infer it as today's date: {datetime.date.today().strftime('%Y-%m-%d')}.
     - Example Query: "add an entry to trials, log name, position, age, number - Tianco, ST, 21, 99"
     - Correct Tool Call: `add_log_entry(logbook_name="trials", data={{"name": "Tianco", "position": "ST", "age": 21, "number": 99}})`
     </rule>

     - **NEW EXAMPLE:** The user might provide data in a "list of columns, list of values" format. You must correctly map them.
     - **User Query:** "add an entry to trials, log name, position, age, number - Tianco, ST, 21, 99"
     - **Your Logic:**
     1. Identify the logbook: `trials`.
     2. Identify the columns: `name`, `position`, `age`, `number`.
     3. Identify the values: `Tianco`, `ST`, `21`, `99`.
     4. Map them correctly.
      - **Correct Tool Call:** `add_log_entry(logbook_name="trials", data={{"name": "Tianco", "position": "ST", "age": 21, "number": 99}})`
     </rule>

        <rule name="General">
        - Your ONLY output MUST be a single, valid tool call based on the user's most recent query. Do not add any conversational text.
        </rule>
        </rules>
        """
        
        intent = "log_entry" if "log" in query.lower() or "entry" in query.lower() or "add" in query.lower() else self._classify_intent(query, chat_history)
        
        messages = [{"role": "system", "content": system_prompt}] + chat_history
        if intent != 'new_search' and last_result_df is not None and not last_result_df.empty:
            messages.append({"role": "system", "content": f"<context>The user is viewing players with these columns: {json.dumps(list(last_result_df.columns))}</context>"})
        messages.append({"role": "user", "content": query})

        # --- SPRINT 2 MODIFICATION: The new `add_log_entry` tool is now available to the agent ---
        all_tools = [new_search, filter_and_sort, create_plot, add_log_entry, query_logbook]
        tools = [{"type": "function", "function": convert_to_openai_function(f)} for f in all_tools]
        
        try:
            response = self.client.chat.completions.create(model=self.model_name, messages=messages, tools=tools, tool_choice="auto")
            response_message = response.choices[0].message
        except Exception as e:
            return {"summary_text": f"Error contacting AI service: {e}", "dataframe": None, "raw_dataframe": None, "plotly_fig": None, "tool_call": None}

        if not response_message.tool_calls:
            return {"summary_text": "I'm sorry, I couldn't determine the next action. Please rephrase.", "dataframe": None, "raw_dataframe": None, "plotly_fig": None, "tool_call": None}

        tool_call = response_message.tool_calls[0]
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)

        # --- NEW: Pre-emptive Argument Validation ---
        if function_name == 'add_log_entry':
            if 'data' not in function_args or 'logbook_name' not in function_args:
                # This catches cases where the LLM fails to provide all necessary arguments.
                error_message = "I can do that, but I need you to specify both the logbook name and the data to add. For example: 'Add an entry to the wellness_log with 8 hours sleep and a soreness of 3.'"
                return {"summary_text": error_message, "dataframe": None, "raw_dataframe": None, "plotly_fig": None, "tool_call": None}
        
        print(f"DEBUG: LLM chose tool '{function_name}' with args: {function_args}")

        result_df = None
        plotly_fig = None
        display_df = None
        
        try:
            if function_name == 'new_search':
                archetype = function_args.get("archetype_name")
                category = ARCHETYPE_TO_POSITION_CATEGORY.get(archetype)
                initial_df = full_df[full_df['primary_position'].isin(POSITION_GROUPINGS.get(category, []))] if category else full_df
                fit_score_col_name = f"fit_score_{archetype.lower().replace(' ', '_').replace('/', '_')}"
                initial_df = initial_df.copy()
                initial_df[fit_score_col_name] = _calculate_fit_score(initial_df, full_df, archetype)
                result_df = _execute_search_and_filter(df=initial_df, normalization_context_df=full_df, filters=function_args.get("filters", []), sort_by=fit_score_col_name, sort_ascending=False)
            elif function_name == 'filter_and_sort':
                result_df = _execute_search_and_filter(df=last_result_df, normalization_context_df=full_df, **function_args)
            elif function_name == 'create_plot':
                plotly_fig = _internal_create_plot(df=last_result_df, full_df=full_df, **function_args)
            
            # --- SPRINT 2 MODIFICATION: Execution logic for the new tool ---
            elif function_name == 'add_log_entry':
            # Pass the current state to the tool, and capture the updated state it returns
            updated_logbooks = _internal_add_log_entry(current_logbooks, **function_args)
            display_df = updated_logbooks[function_args['logbook_name']]
            # Add the updated state to the response dictionary
            response['updated_logbooks'] = updated_logbooks

        elif function_name == 'query_logbook':
            # Pass the current state to the tool
            answer_text = self._internal_query_logbook(current_logbooks, **function_args)
            summary_text = answer_text
             # The internal function returns a simple string answer.
             answer_text = self._internal_query_logbook(**function_args)
             # We will hijack the 'summary_text' to deliver the answer directly to the UI.
             summary_text = answer_text
             # Ensure no dataframe is displayed for this type of response.
             display_df = None
            result_df = None

        except (ValueError, KeyError) as e:
            return {"summary_text": f"I couldn't complete that request: {e}", "dataframe": None, "raw_dataframe": None, "plotly_fig": None, "tool_call": None}
            
        # If a summary hasn't been generated by a tool, call our new safe method.
if not summary_text:
    summary_text = self._generate_summary(query, function_name, function_args)
        
        # --- SPRINT 2 MODIFICATION: Final Response Handling ---
        # If a player search was performed, use the existing logic to create a formatted display DataFrame.
        # Otherwise, the display_df (containing the updated logbook) will be used.
        if result_df is not None and function_name != 'add_log_entry':
            base_cols = ['full_name', 'age', 'primary_position']
            fit_score_cols = sorted([c for c in result_df.columns if 'fit_score' in c])
            archetype_for_this_turn = active_archetype
            if function_name == 'new_search': archetype_for_this_turn = function_args.get("archetype_name")
            elif function_name == 'filter_and_sort': archetype_for_this_turn = function_args.get('add_archetype_as_column', active_archetype)
            key_metric_cols = list(ARCHETYPES.get(archetype_for_this_turn, {}).get('key_metrics', {}).keys())
            used_cols = [col for col in [function_args.get('sort_by')] + [f.get('column') for f in function_args.get('filters', [])] if col]
            final_display_cols = list(dict.fromkeys([col for col in base_cols + fit_score_cols + key_metric_cols + used_cols if col in result_df.columns]))
            final_display_df = result_df[final_display_cols].copy()
            for col in fit_score_cols:
                final_display_df[col] = final_display_df[col].round(3)
            display_df = final_display_df

response.update({
    "summary_text": summary_text, 
    "dataframe": display_df, 
    "plotly_fig": plotly_fig, 
    "raw_dataframe": result_df if function_name not in ['add_log_entry', 'query_logbook'] else None,
    "tool_call": {"name": function_name, "arguments": function_args},
 })
return response 

    # ---------------------- CHANGE 1.2: ADDITION START ---------------------
    def generate_on_demand_insight(self, player_name: str, full_df: pd.DataFrame, active_archetype: str) -> str:
        """
        Generates an "Analyst's Note" for a single, specific player chosen by the user.

        This method serves as a dedicated entry point for the on-demand UI feature. It bypasses
        the main chat and tool-use pipeline for a faster, more direct response.

        Args:
            player_name (str): The 'full_name' of the player to be analyzed.
            full_df (pd.DataFrame): The complete, unfiltered dataset, required for percentile calculations.
            active_archetype (str): The primary archetype context for the analysis.

        Returns:
            str: A formatted Markdown string containing the "Analyst's Note", 
                 or an error message if the analysis could not be completed.
        """
        print(f"DEBUG: Received on-demand insight request for '{player_name}' with archetype '{active_archetype}'.")
        try:
            # Find the specific player's data from the full dataset.
            # It's crucial to use full_df to get the complete, original data for the player.
            player_series = full_df[full_df['full_name'] == player_name].iloc[0]

            if player_series.empty:
                return "**Analysis Error:** Could not find the specified player in the dataset."
            
            if not active_archetype:
                 return "**Analysis Error:** An active archetype is required to generate an analyst note."

            # Call the insight engine with the required context.
            analyst_note = self.insight_engine.generate_analyst_note(
                player_data=player_series,
                full_dataset=full_df,
                active_archetype=active_archetype
            )
            return analyst_note

        except IndexError:
            # This error occurs if the player_name is not found in the dataframe.
            print(f"ERROR: Could not find player '{player_name}' in generate_on_demand_insight.")
            return f"**Analysis Error:** Could not find player '{player_name}' in the dataset."
        except Exception as e:
            # Catch any other unexpected errors during insight generation.
            print(f"ERROR: An unexpected error occurred in generate_on_demand_insight: {e}")
            return f"**Analysis Error:** An unexpected problem occurred while generating the note. Details: {e}"
    # ---------------------- CHANGE 1.2: ADDITION END -----------------------

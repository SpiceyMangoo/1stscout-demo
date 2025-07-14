import pandas as pd
import json
import os
from typing import Tuple, Dict, Any, List

import plotly.graph_objects as go
import plotly.express as px

from openai import OpenAI
from langchain_core.utils.function_calling import convert_to_openai_function
from config.settings import OPENAI_API_KEY, ARCHETYPES_PATH, SYNONYM_LIBRARY_PATH, NLU_MAPPINGS_PATH

### INSIGHT ENGINE INTEGRATION (1/3) - IMPORT ###
from insights.insight_engine import InsightEngine


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

class ScoutAgent:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model_name = "gpt-4.1-nano-2025-04-14"
        
        ### INSIGHT ENGINE INTEGRATION (2/3) - INSTANTIATION ###
        self.insight_engine = InsightEngine(archetypes=ARCHETYPES)
    
    def _classify_intent(self, query: str, chat_history: list) -> str:
        """
        A simple, fast classification call to determine if the user wants a new search or a refinement.
        """
        valid_archetypes = list(ARCHETYPES.keys())
        archetype_list_for_prompt = "\n".join(f"- '{name}'" for name in valid_archetypes)

        classifier_prompt = f"""
        You are an intent classifier. Your only job is to determine if the user's request is for a 'new_search' or a 'refinement'.
        - A 'new_search' happens when the user explicitly mentions a player archetype, signalling they want to start over.
        - A 'refinement' happens when the user asks to filter, sort, plot, or add information to the players they are already looking at.

        Valid Archetypes:
        {archetype_list_for_prompt}

        Based on the user's latest query, classify the intent as 'new_search' or 'refinement'.
        Your response MUST be one word: either 'new_search' or 'refinement'.
        """
        
        messages = [{"role": "system", "content": classifier_prompt}]
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": query})

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0,
                max_tokens=10 
            )
            intent = response.choices[0].message.content.strip().lower()
            if intent not in ['new_search', 'refinement']:
                return 'refinement'
            return intent
        except Exception as e:
            print(f"DIAGNOSTIC: Intent classification failed: {e}")
            return 'refinement'

    def process_query(self, query: str, chat_history: list, full_df: pd.DataFrame, last_result_df: pd.DataFrame, active_archetype: str) -> Dict[str, Any]:
        valid_archetypes = list(ARCHETYPES.keys())
        archetype_list_for_prompt = "\n".join(f"- '{name}'" for name in valid_archetypes)
        
        column_list_for_prompt = json.dumps(list(full_df.columns)) if full_df is not None else "[]"

        system_prompt = f"""You are an expert AI assistant for a football scout. Your job is to translate user requests into precise tool calls.
        <rules>
        <rule>
        <name>Tool Choice Logic</name>
        - Use `new_search` ONLY when the user wants to start a completely fresh search, identified by a new primary archetype (e.g., "find all inside forwards", "show me box to box midfielders").
        - Use `filter_and_sort` for ALL other cases of refining the current list of players.
        - Use `create_plot` when the user asks to 'plot', 'visualize', 'chart', 'graph', or 'compare' data.
        </rule>
        <rule>
        <name>New Search Construction</name>
        - A `new_search` MUST have an `archetype_name`.
        - If the user includes other conditions in their initial prompt, like age (e.g., "u26", "under 26"), you MUST add these as a `filters` list. Example: "find inside forwards u26" -> `new_search(archetype_name="Inside Forward", filters=[{{"column": "age", "operator": "less_than", "value": 26}}])`.
        <valid_archetypes>{archetype_list_for_prompt}</valid_archetypes>
        </rule>
        <rule>
        <name>Filter and Sort Construction</name>
        - A filter is a dictionary: {{"column": "...", "operator": "...", "value": ...}}. Valid operators: `greater_than`, `less_than`, `equal_to`, `contains`, `is_in`.
        - For requests like "show players with npxg p90 above 0.48", construct a filter: `{{"column": "npxg_p90", "operator": "greater_than", "value": 0.48}}`.
        - For requests like "who are also pressing forwards?", use the `add_archetype_as_column` parameter: `add_archetype_as_column="Pressing Forward"`.
        </rule>
        <rule>
        <name>Fit Score Filtering</name>
        - If the user says "fit score", you must determine the correct column name. The list of available columns will be in the format `fit_score_[archetype_name]`.
        - You MUST use this full, exact name in your filter. Example: `filter_and_sort(filters=[{{"column": "fit_score_inside_forward", "operator": "greater_than", "value": 0.8}}])`.
        </rule>
        <rule>
        <name>Available Columns</name>
        - The columns available for filtering, sorting, and plotting will be provided in the chat history context. Always refer to the latest available list. A generic list is provided here for reference: {column_list_for_prompt}
        - Do not invent column names. Always use a name from the available columns.
        </rule>
        </rules>
        Your ONLY output MUST be a single, valid tool call. Do not add any conversational text.
        """
        
        intent = self._classify_intent(query, chat_history)
        print(f"DIAGNOSTIC: Classified intent as '{intent}'.")

        context_provider_df = last_result_df if last_result_df is not None else full_df
        messages = [{"role": "system", "content": system_prompt}] + chat_history
        
        if intent != 'new_search' and context_provider_df is not None and not context_provider_df.empty:
            latest_columns = json.dumps(list(context_provider_df.columns))
            messages.append({"role": "system", "content": f"<context>The user is currently viewing players with these available columns for filtering: {latest_columns}</context>"})
            print("DIAGNOSTIC: Appending existing search context to prompt.")
        else:
            print("DIAGNOSTIC: Intent is 'new_search', context will not be appended.")
            
        messages.append({"role": "user", "content": query})

        tools = [{"type": "function", "function": convert_to_openai_function(f)} for f in [new_search, filter_and_sort, create_plot]]
        
        try:
            response = self.client.chat.completions.create(model=self.model_name, messages=messages, tools=tools, tool_choice="auto")
            response_message = response.choices[0].message
        except Exception as e:
            print(f"FATAL: OpenAI API call failed: {e}")
            return {"summary_text": f"I had a problem contacting the AI service. Details: {e}", "dataframe": None, "raw_dataframe": None, "plotly_fig": None, "tool_call": None}

        if not response_message.tool_calls:
            return {"summary_text": "I'm sorry, I couldn't determine the next action. Could you please rephrase your request?", "dataframe": None, "raw_dataframe": None, "plotly_fig": None, "tool_call": None}

        tool_call = response_message.tool_calls[0]
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        print(f"DEBUG: LLM chose tool '{function_name}' with args: {function_args}")

        result_df = None
        plotly_fig = None
        
        archetype_for_this_turn = active_archetype
        if function_name == 'new_search':
            archetype_for_this_turn = function_args.get("archetype_name")
        elif function_name == 'filter_and_sort':
            archetype_for_this_turn = function_args.get('add_archetype_as_column', active_archetype)

        try:
            if function_name == 'new_search':
                if full_df is None: raise ValueError("No data is available to search. Please upload a CSV file first.")
                archetype = function_args.get("archetype_name")
                if not archetype: raise ValueError("A new search must start with a primary archetype.")
                
                category = ARCHETYPE_TO_POSITION_CATEGORY.get(archetype)
                initial_df = full_df[full_df['primary_position'].isin(POSITION_GROUPINGS.get(category, []))] if category else full_df

                fit_score_col_name = f"fit_score_{archetype.lower().replace(' ', '_').replace('/', '_')}"
                initial_df = initial_df.copy()
                initial_df[fit_score_col_name] = _calculate_fit_score(initial_df, full_df, archetype)
                
                filters = function_args.get("filters", [])
                result_df = _execute_search_and_filter(
                    df=initial_df,
                    normalization_context_df=full_df,
                    filters=filters,
                    sort_by=fit_score_col_name,
                    sort_ascending=False
                )

            elif function_name == 'filter_and_sort':
                if last_result_df is None: raise ValueError("There are no previous search results to refine.")
                result_df = _execute_search_and_filter(df=last_result_df, normalization_context_df=full_df, **function_args)
            
            elif function_name == 'create_plot':
                if last_result_df is None or last_result_df.empty: raise ValueError("I can't create a plot because you aren't viewing any players.")
                plotly_fig = _internal_create_plot(df=last_result_df, full_df=full_df, **function_args)

        except (ValueError, KeyError) as e:
            error_message = f"I couldn't complete that request. {e}"
            print(error_message)
            return {"summary_text": error_message, "dataframe": None, "raw_dataframe": None, "plotly_fig": None, "tool_call": None}
            
        summary_prompt = "You are an AI Football Scout. Your tool call was successful. Based on the original query and the tool called, write a brief, friendly confirmation message explaining what you did."
        summary_response = self.client.chat.completions.create(
            model=self.model_name, messages=[{"role": "system", "content": summary_prompt}, {"role": "user", "content": f"Query: {query}, Tool: {function_name}, Args: {json.dumps(function_args)}"}]
        )
        summary_text = summary_response.choices[0].message.content
        
        display_df = None

        if result_df is not None:
            base_cols = ['full_name', 'age', 'primary_position']
            fit_score_cols = sorted([c for c in result_df.columns if 'fit_score' in c])
            
            key_metric_cols = []
            if archetype_for_this_turn and archetype_for_this_turn in ARCHETYPES:
                key_metric_cols = list(ARCHETYPES[archetype_for_this_turn]['key_metrics'].keys())

            used_cols = []
            if sort_by_col := function_args.get('sort_by'): used_cols.append(sort_by_col)
            if filters := function_args.get('filters'):
                for f in filters: used_cols.append(f['column'])
            
            display_cols = base_cols + fit_score_cols + key_metric_cols + used_cols
            final_display_cols = list(dict.fromkeys([col for col in display_cols if col in result_df.columns]))
            
            final_display_df = result_df[final_display_cols].copy()
            for col in fit_score_cols:
                final_display_df[col] = final_display_df[col].round(3)
            display_df = final_display_df
            
            # --------------------- CHANGE 1.1: REMOVAL START ---------------------
            # The entire "INSIGHT ENGINE INTEGRATION (3/3) - INVOCATION" block has been removed from here.
            # The logic that automatically generated an analyst_note for the top player is gone.
            # ---------------------- CHANGE 1.1: REMOVAL END ----------------------
        
        return {
            "summary_text": summary_text, 
            "dataframe": display_df, 
            "plotly_fig": plotly_fig, 
            "raw_dataframe": result_df,
            "tool_call": {"name": function_name, "arguments": function_args},
            # The "analyst_note" key has been removed from this dictionary
        }

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

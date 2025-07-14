import pandas as pd
import json
from openai import OpenAI
from typing import Dict, Any, List, Optional

# Note: We will need to add INSIGHTS_PERSONA_PATH to the settings file.
from config.settings import OPENAI_API_KEY, INSIGHTS_PERSONA_PATH

class InsightEngine:
    """
    Analyzes a player's data to generate qualitative insights.
    This engine encapsulates the logic for identifying statistical extremes and
    conceptual anomalies, then uses an LLM to synthesize these findings into
    a narrative "Analyst's Note" based on a defined persona.
    """

    def __init__(self, archetypes: Dict[str, Any]):
        """
        Initializes the InsightEngine.

        Args:
            archetypes (Dict[str, Any]): The loaded dictionary of player archetypes and their key metrics.
        """
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model_name = "gpt-4.1-nano-2025-04-14"
        self.archetypes = archetypes
        try:
            with open(INSIGHTS_PERSONA_PATH, 'r') as f:
                self.master_prompt = f.read()
        except FileNotFoundError:
            # Fallback in case the persona file is missing
            self.master_prompt = "You are an AI football scout. Write a brief analysis."
            print(f"WARNING: Persona file not found at {INSIGHTS_PERSONA_PATH}. Using a fallback prompt.")
        except Exception as e:
            self.master_prompt = "You are an AI football scout. Write a brief analysis."
            print(f"ERROR: Could not load persona file. Details: {e}")


    def _calculate_percentiles(self, player_series: pd.Series, full_df: pd.DataFrame) -> Optional[pd.Series]:
        """
        Calculates the percentile rank for each of a player's stats relative to the full dataset.

        Args:
            player_series (pd.Series): The data for the single player to analyze.
            full_df (pd.DataFrame): The full dataset for calculating percentile context.

        Returns:
            Optional[pd.Series]: A Series where index is the stat name and value is the percentile (0-100).
                                 Returns None if player data is not found.
        """
        if player_series.name not in full_df.index:
            return None
            
        # Use rank(pct=True) for efficient, vectorized percentile calculation
        percentiles = full_df.rank(pct=True).loc[player_series.name] * 100
        return percentiles.round(0)

    def generate_analyst_note(self, player_data: pd.Series, full_dataset: pd.DataFrame, active_archetype: str) -> Optional[str]:
        """
        Generates a full "Analyst's Note" for a given player.

        This method performs the core analytical workflow:
        1. Calculates percentiles for the player's stats.
        2. Identifies the top 4 strengths and weaknesses based on their primary archetype.
        3. Finds a "WOW" conceptual anomaly by checking for high performance in contrasting archetypes.
        4. Synthesizes these findings into a narrative using an LLM call guided by the master persona prompt.

        Args:
            player_data (pd.Series): The data for the single player.
            full_dataset (pd.DataFrame): The entire dataset for context.
            active_archetype (str): The primary archetype of the player.

        Returns:
            Optional[str]: A formatted Markdown string containing the "Analyst's Note", or None if an error occurs.
        """
        player_percentiles = self._calculate_percentiles(player_data, full_dataset)
        if player_percentiles is None:
            return None

        # 1. Identify Strengths and Weaknesses
        archetype_metrics = self.archetypes.get(active_archetype, {}).get("key_metrics", {})
        if not archetype_metrics:
            return None # Cannot proceed without metrics for the active archetype

        # Filter percentiles to only the metrics relevant to the player's archetype
        relevant_percentiles = player_percentiles[archetype_metrics.keys()].dropna()
        
        strengths = relevant_percentiles.nlargest(4)
        weaknesses = relevant_percentiles.nsmallest(4)

        # 2. Identify Conceptual Anomaly ("WOW" Insight)
        anomaly = None
        for archetype_name, details in self.archetypes.items():
            if archetype_name == active_archetype:
                continue # Skip the player's own archetype

            # Get the single most important metric for this "foreign" archetype
            foreign_metrics = details.get("key_metrics", {})
            if not foreign_metrics:
                continue
            
            primary_foreign_metric = max(foreign_metrics, key=foreign_metrics.get)

            # Check the player's percentile in this specific metric
            if primary_foreign_metric in player_percentiles and player_percentiles[primary_foreign_metric] >= 90:
                anomaly = {
                    "archetype": archetype_name,
                    "metric": primary_foreign_metric,
                    "percentile": player_percentiles[primary_foreign_metric]
                }
                break # Found the first anomaly, so we stop

        # 3. Synthesize with LLM
        structured_input = f"""
        * Player Name: {player_data.get('full_name', 'N/A')}
        * Primary Archetype: {active_archetype}
        * Identified Strengths:
        {json.dumps(strengths.to_dict(), indent=4)}
        * Identified Weaknesses:
        {json.dumps(weaknesses.to_dict(), indent=4)}
        * Conceptual Anomaly:
        {json.dumps(anomaly, indent=4) if anomaly else "None Found"}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.master_prompt},
                    {"role": "user", "content": structured_input}
                ],
                temperature=0.4 # A little creativity for better narrative flow
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"ERROR: Insight Engine LLM call failed: {e}")
            return f"**Analysis Error:** Could not generate the analyst's note due to a connection issue. Details: {e}"

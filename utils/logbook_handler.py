import pandas as pd
import streamlit as st
from io import BytesIO, StringIO
from typing import List, Dict, Any

# (The create_logbook_template function from Sprint 1 remains unchanged)
def create_logbook_template(logbook_name: str, metrics: List[Dict[str, str]]) -> bytes:
    """
    Creates an empty pandas DataFrame based on user-defined metrics, adds a default
    'date' column, and converts the DataFrame to a CSV formatted byte stream for downloading.
    """
    column_names = [metric['name'].strip().lower().replace(' ', '_') for metric in metrics]
    if 'date' not in column_names:
        column_names.insert(0, 'date')
    df = pd.DataFrame(columns=column_names)
    output_buffer = BytesIO()
    df.to_csv(output_buffer, index=False, encoding='utf-8')
    processed_data = output_buffer.getvalue()
    return processed_data

# --- NEW FUNCTION 1: load_logbook ---
def load_logbook(uploaded_file: Any) -> None:
    """
    Loads a user-uploaded CSV logbook into the session state.

    This function takes a Streamlit UploadedFile object, reads it into a pandas
    DataFrame, creates a sanitized, machine-readable key from the filename,
    and stores the DataFrame in a dedicated dictionary within st.session_state.

    Args:
        uploaded_file: The file object from a Streamlit file_uploader widget.
    """
    if uploaded_file is None:
        return

    # Sanitize the filename to use as a dictionary key.
    # e.g., "U19 Wellness Log.csv" -> "u19_wellness_log"
    file_name = uploaded_file.name
    logbook_key = file_name.lower().replace('.csv', '').replace(' ', '_')

    try:
        # Read the CSV data into a pandas DataFrame.
        string_data = StringIO(uploaded_file.getvalue().decode('utf-8'))
        df = pd.read_csv(string_data)

        # Store the loaded DataFrame in the session state dictionary.
        st.session_state['logbooks'][logbook_key] = df
        st.success(f"Successfully loaded and integrated logbook: '{file_name}'")
        print(f"DIAGNOSTIC: Loaded logbook '{logbook_key}' with columns: {df.columns.tolist()}")

    except Exception as e:
        st.error(f"Error loading logbook '{file_name}': {e}")
        print(f"ERROR: Failed to load logbook '{file_name}'. Details: {e}")

# --- NEW FUNCTION 2: get_all_logbook_schemas ---
def get_all_logbook_schemas() -> str:
    """
    Inspects all loaded logbooks in the session state and generates a
    formatted string describing their schemas (name and columns).

    This function is critical for dynamic prompt engineering. It provides the
    agent with the necessary "world knowledge" of what custom databases are
    available and what data they can contain.

    Returns:
        A formatted string detailing the schemas of all loaded logbooks,
        ready to be injected into the agent's system prompt.
        Returns an empty string if no logbooks are loaded.
    """
    if 'logbooks' not in st.session_state or not st.session_state['logbooks']:
        return ""

    schema_descriptions = []
    for logbook_name, df in st.session_state['logbooks'].items():
        columns = ", ".join(df.columns.tolist())
        description = (
            f"<logbook>\n"
            f"  <name>{logbook_name}</name>\n"
            f"  <columns>{columns}</columns>\n"
            f"</logbook>"
        )
        schema_descriptions.append(description)

    if not schema_descriptions:
        return "No custom logbooks are currently loaded."

    return "\n".join(schema_descriptions)
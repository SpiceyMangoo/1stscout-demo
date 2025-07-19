import pandas as pd
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
def load_logbook(current_logbooks: Dict[str, pd.DataFrame], uploaded_file: Any) -> Dict[str, pd.DataFrame]:
    """Loads a user-uploaded CSV into the provided logbooks dictionary."""
    file_name = uploaded_file.name
    logbook_key = file_name.lower().replace('.csv', '').replace(' ', '_')
    try:
        string_data = StringIO(uploaded_file.getvalue().decode('utf-8'))
        df = pd.read_csv(string_data)
        current_logbooks[logbook_key] = df
        print(f"DIAGNOSTIC: Loaded logbook '{logbook_key}' with columns: {df.columns.tolist()}")
    except Exception as e:
        print(f"ERROR: Failed to load logbook '{file_name}'. Details: {e}")
    return current_logbooks

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
def get_all_logbook_schemas(current_logbooks: Dict[str, pd.DataFrame]) -> str:
    """Inspects the provided logbooks dictionary and generates a schema string."""
    if not current_logbooks:
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

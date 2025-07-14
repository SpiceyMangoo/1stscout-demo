import pandas as pd
import io
from typing import Dict, Any

def process_uploaded_csv(uploaded_file: Any, synonym_library: Dict[str, Any]) -> pd.DataFrame:
    """
    Processes a user-uploaded CSV file, standardizing its column headers against a canonical schema.

    This function takes a file-like object (e.g., from a Streamlit file uploader),
    reads it into a pandas DataFrame, and then attempts to map its existing column
    headers to the standardized, canonical names defined in the synonym library. This
    is a critical step to ensure that user-provided data, which may have inconsistent
    naming, can be understood and processed by the agent.

    Args:
        uploaded_file: A file-like object (e.g., io.BytesIO, Streamlit UploadedFile)
                       containing the CSV data.
        synonym_library: The loaded JSON from nlu_synonym_library.json, which contains
                         the mapping from canonical names to a list of possible synonyms.

    Returns:
        A pandas DataFrame with its column headers cleaned and mapped to the
        canonical schema where possible. Columns without a defined mapping are
        retained with their original names to ensure no data is lost.
        
    Raises:
        ValueError: If the uploaded file cannot be parsed as a valid CSV.
    """
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        # If pandas cannot read the file, raise an error to be caught by the UI
        raise ValueError(f"Could not parse the uploaded file. Please ensure it is a valid CSV. Error: {e}")

    # Create a reverse mapping from any possible synonym to its single canonical name.
    # This allows for fast lookups. The keys are standardized (lowercase, stripped space)
    # to handle variations in user CSV files.
    reverse_synonym_map = {}
    for canonical_name, synonyms in synonym_library.get("synonym_library", {}).items():
        for synonym in synonyms:
            reverse_synonym_map[synonym.strip().lower()] = canonical_name

    # Map the original headers to the new canonical headers.
    new_columns = []
    mapped_cols_report = {}
    unmapped_cols_report = []

    for original_col_name in df.columns:
        standardized_col_name = original_col_name.strip().lower()
        
        if standardized_col_name in reverse_synonym_map:
            # A mapping was found; use the canonical name.
            canonical_col = reverse_synonym_map[standardized_col_name]
            new_columns.append(canonical_col)
            mapped_cols_report[original_col_name] = canonical_col
        else:
            # No mapping was found; retain the original column name.
            new_columns.append(original_col_name)
            unmapped_cols_report.append(original_col_name)
    
    df.columns = new_columns

    # Log a report to the console for diagnostics and debugging.
    # This is invaluable for the developer to see how user data is being interpreted.
    print("--- CSV Processing Report ---")
    if mapped_cols_report:
        print(f"Successfully mapped {len(mapped_cols_report)} columns:")
        for original, new in mapped_cols_report.items():
            print(f"  - '{original}' -> '{new}'")
    
    if unmapped_cols_report:
        print(f"Could not find a mapping for {len(unmapped_cols_report)} columns (retained original names):")
        for col in unmapped_cols_report:
            print(f"  - '{col}'")
    print("--------------------------")

    return df
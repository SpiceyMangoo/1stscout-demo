# diagnostic_script.py
import pandas as pd
import os

# This script is designed to be run from the root of your project directory.
# It will load the user's CSV and print its column headers.

# Construct the path to the CSV file
try:
    csv_path = os.path.join('database', 'sample_data.csv')
    
    if not os.path.exists(csv_path):
        print(f"ERROR: The file could not be found at the expected path: {csv_path}")
        print("Please ensure that 'sample_data.csv' exists inside the 'database' directory.")
    else:
        # Load the CSV into a pandas DataFrame
        df = pd.read_csv(csv_path)
        
        # Get the list of column headers
        column_headers = df.columns.tolist()
        
        # Print the headers for analysis
        print("--- DIAGNOSTIC SCRIPT OUTPUT ---")
        print("Detected Column Headers in 'sample_data.csv':")
        print(column_headers)
        print("--- END OF DIAGNOSTIC ---")

except Exception as e:
    print(f"An unexpected error occurred: {e}")
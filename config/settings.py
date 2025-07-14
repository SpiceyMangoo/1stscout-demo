import os
from dotenv import load_dotenv

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to the .env file
dotenv_path = os.path.join(current_dir, '.env')

# Load the .env file
load_dotenv(dotenv_path=dotenv_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Define absolute paths for data files to avoid relative path issues
BASE_DIR = os.path.abspath(os.path.join(current_dir, os.pardir))
DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'sample_data.csv')
ARCHETYPES_PATH = os.path.join(BASE_DIR, 'database', 'archetypes.json')
SYNONYM_LIBRARY_PATH = os.path.join(BASE_DIR, 'database', 'nlu_synonym_library.json')
NLU_MAPPINGS_PATH = os.path.join(BASE_DIR, 'database', 'nlu_mappings.json')
INSIGHTS_PERSONA_PATH = os.path.join(BASE_DIR, 'database', 'insight_persona.md')
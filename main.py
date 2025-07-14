import streamlit as st
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.append(PROJECT_ROOT)

from ui.web_ui import WebUI

def main():
    # --- BEGIN MODIFICATION ---
    # Comment out the following 5 lines
    # st.set_page_config(
    #     page_title="1stScout Demo",
    #     page_icon="⚽",
    #     layout="wide"
    # )
    # --- END MODIFICATION ---
    
    app = WebUI()
    app.run()

if __name__ == "__main__":
    main()
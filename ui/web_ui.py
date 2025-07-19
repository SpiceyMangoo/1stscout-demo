import streamlit as st
import pandas as pd
import json
import uuid # Import the uuid library to generate unique keys for dynamic widgets

from agent.agent_core import ScoutAgent, SYNONYM_LIBRARY
from utils.data_handler import process_uploaded_csv
# Import the new function from our logbook handler
from utils.logbook_handler import create_logbook_template, load_logbook

class WebUI:
    def __init__(self):
        """Initializes the WebUI, setting the page configuration and instantiating the agent."""
        st.set_page_config(
            page_title="1stScout Demo",
            page_icon="⚽",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        st.title("1stScout Demo ⚽")
        st.caption("v1.4 (Logbook Creator MVP)")
        
        try:
            self.agent = ScoutAgent() 
            
        except Exception as e:
            st.error(f"Fatal Initialization Error: Could not start the AI agent. Details: {e}")
            st.stop()

    def _initialize_session_state(self):
        """Sets up the session state variables if they don't already exist."""
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "data_loaded" not in st.session_state:
            st.session_state.data_loaded = False
        if "uploaded_file_name" not in st.session_state:
            st.session_state.uploaded_file_name = None
        if "full_df" not in st.session_state:
            st.session_state.full_df = None
        if "raw_df_history" not in st.session_state:
            st.session_state.raw_df_history = []
        if "active_archetype" not in st.session_state:
            st.session_state.active_archetype = None
        if "selected_player_for_note" not in st.session_state:
            st.session_state.selected_player_for_note = None
        if "current_analyst_note" not in st.session_state:
            st.session_state.current_analyst_note = None
        if 'logbooks' not in st.session_state:
            st.session_state['logbooks'] = {}
        if 'new_logbook_metrics' not in st.session_state:
            st.session_state.new_logbook_metrics = []

    def _render_creator_wizard(self):
        """
        Renders the complete user interface for the Logbook Creator wizard.
        This function is self-contained and manages the state of the creation process.
        """
        st.subheader("2. Create a New Logbook Template")
        st.info("Define the metrics for your custom logbook and download the CSV template.", icon="✍️")

        logbook_name = st.text_input("New Logbook Name", placeholder="e.g., 'U19 Wellness Log'")

        st.markdown("**Define Your Metrics:**")
        
        # --- Display the list of metrics added so far ---
        # This loop dynamically displays the metrics the user has defined.
        for i, metric in enumerate(st.session_state.new_logbook_metrics):
            col1, col2, col3 = st.columns([4, 3, 1])
            col1.text_input("Metric Name", value=metric['name'], key=f"metric_name_{metric['id']}", disabled=True)
            col2.text_input("Data Type", value=metric['type'], key=f"metric_type_{metric['id']}", disabled=True)
            if col3.button("❌", key=f"delete_metric_{metric['id']}", help="Remove this metric"):
                st.session_state.new_logbook_metrics.pop(i)
                st.rerun()

        # --- Input controls for adding a new metric ---
        with st.form(key="add_metric_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            new_metric_name = col1.text_input("New Metric Name", key="new_metric_name_input")
            new_metric_type = col2.selectbox("Data Type", ["Number", "Text", "Date"], key="new_metric_type_input")
            
            submitted = st.form_submit_button("Add Metric")
            if submitted and new_metric_name:
                st.session_state.new_logbook_metrics.append({
                    "id": str(uuid.uuid4()), # Assign a unique ID for stable widget keys
                    "name": new_metric_name,
                    "type": new_metric_type
                })
                st.rerun()
            elif submitted and not new_metric_name:
                st.warning("Metric name cannot be empty.")

        # --- The Download Button Logic (The "Engine") ---
        # This section only appears if the user has defined a name and at least one metric.
        if logbook_name and st.session_state.new_logbook_metrics:
            st.divider()
            
            # The core of the engine: call our handler to get the CSV data.
            try:
                csv_data = create_logbook_template(logbook_name, st.session_state.new_logbook_metrics)
                
                # Sanitize the logbook name to create a valid, safe filename for download.
                safe_filename = "".join(c for c in logbook_name if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
                
                st.download_button(
                   label="✅ Download Logbook Template",
                   data=csv_data,
                   file_name=f"{safe_filename}.csv",
                   mime="text/csv",
                   use_container_width=True,
                )
            except Exception as e:
                st.error(f"Could not generate template: {e}")

    def _render_sidebar(self):
        """Renders the sidebar for file uploading and the new creator wizard."""
        with st.sidebar:
            st.header("Controls")
            st.subheader("1. Upload Your Data")
            
            uploaded_file = st.file_uploader(
                "Upload your player data CSV file.",
                type="csv",
                help="The file should contain player statistics with one player per row."
            )
            
            if uploaded_file is not None and uploaded_file.name != st.session_state.uploaded_file_name:
                with st.spinner(f"Processing '{uploaded_file.name}'..."):
                    try:
                        # (Existing logic remains unchanged)
                        processed_df = process_uploaded_csv(uploaded_file, SYNONYM_LIBRARY)
                        st.session_state.full_df = processed_df
                        st.session_state.data_loaded = True
                        st.session_state.messages = []
                        st.session_state.raw_df_history = []
                        st.session_state.uploaded_file_name = uploaded_file.name
                        st.session_state.active_archetype = None 
                        st.session_state.current_analyst_note = None
                        st.session_state.selected_player_for_note = None
                        st.success("Data processed successfully!")
                        st.info("You can now chat with the Copilot in the main window.")
                        
                    except ValueError as e:
                        st.error(f"File Processing Error: {e}")
                        st.session_state.data_loaded = False
                        st.session_state.uploaded_file_name = None

            # --- RENDER THE NEW WIZARD IN THE SIDEBAR ---
            st.divider()
            st.subheader("2. Upload Custom Logbooks")
            
            uploaded_logbooks = st.file_uploader(
                "Upload one or more of your custom CSV logbook files here.",
                type="csv",
                accept_multiple_files=True, # Allow multiple logbooks to be uploaded
                key="logbook_uploader"
            )

            if uploaded_logbooks:
                for logbook_file in uploaded_logbooks:
                    # Use the file's unique ID to prevent reprocessing the same file on reruns
                    if (logbook_file.name, logbook_file.size) not in st.session_state.get('processed_logbooks', set()):
                        with st.spinner(f"Loading logbook '{logbook_file.name}'..."):
                            load_logbook(logbook_file) # This function will add it to st.session_state['logbooks']
                        
                        # Add the ID to a set of processed files
                        if 'processed_logbooks' not in st.session_state:
                         st.session_state['processed_logbooks'] = set()
                         st.session_state.processed_logbooks.add((logbook_file.name, logbook_file.size))

            # Move the creator wizard to be the third item
            st.divider()
            st.subheader("3. Create a New Logbook Template")
            self._render_creator_wizard()

    def _render_chat(self):
        """Renders the main chat interface for user interaction."""
        # This part of the function remains the same, rendering previous messages.
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if "dataframe" in msg and msg["dataframe"] is not None:
                    st.dataframe(msg["dataframe"], use_container_width=True, hide_index=True)
                if "plotly_fig" in msg and msg["plotly_fig"] is not None:
                    st.plotly_chart(msg["plotly_fig"], use_container_width=True)

        if st.session_state.get('logbooks'):
            with st.expander("✅ View Loaded Logbooks"):
                for logbook_name, df in st.session_state['logbooks'].items():
                    st.markdown(f"**Logbook: `{logbook_name}`**")
                    st.dataframe(df, use_container_width=True)
                    st.divider()
        
        if prompt := st.chat_input("Find players, or ask a question about the current view..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    last_result_df = st.session_state.raw_df_history[-1] if st.session_state.raw_df_history else None
                    
                    chat_history_for_agent = [
                        {"role": msg["role"], "content": msg["content"]}
                        for msg in st.session_state.messages[:-1]
                    ]

                    agent_response = self.agent.process_query(
                        query=prompt,
                        chat_history=chat_history_for_agent,
                        full_df=st.session_state.full_df,
                        last_result_df=last_result_df,
                        active_archetype=st.session_state.active_archetype
                    )

                    tool_call = agent_response.get("tool_call")
                    if tool_call:
                        tool_name = tool_call.get("name")
                        tool_args = tool_call.get("arguments", {})

                        if tool_name == 'new_search':
                            st.session_state.active_archetype = tool_args.get('archetype_name')
                            # Clear any previous note when starting a new search
                            st.session_state.current_analyst_note = None
                        elif tool_name == 'filter_and_sort' and tool_args.get('add_archetype_as_column'):
                            st.session_state.active_archetype = tool_args.get('add_archetype_as_column')

                    st.markdown(agent_response["summary_text"])
                    if agent_response.get("dataframe") is not None and not agent_response.get("dataframe").empty:
                        st.dataframe(agent_response["dataframe"], use_container_width=True, hide_index=True)
                    if agent_response.get("plotly_fig") is not None:
                        st.plotly_chart(agent_response["plotly_fig"], use_container_width=True)

                    if agent_response.get("raw_dataframe") is not None and not agent_response.get("raw_dataframe").empty:
                        st.session_state.raw_df_history.append(agent_response["raw_dataframe"])
                    elif tool_call and tool_call.get("name") == "create_plot" and last_result_df is not None:
                        st.session_state.raw_df_history.append(last_result_df)
                    
                    # Store the main response without the analyst note
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": agent_response["summary_text"],
                        "dataframe": agent_response.get("dataframe"),
                        "plotly_fig": agent_response.get("plotly_fig"),
                        # Note: 'analyst_note' is no longer part of this message object
                    })

        # --- ON-DEMAND INSIGHTS UI SECTION ---
        # This entire block is new. It runs outside the main chat input loop,
        # allowing users to interact with the most recent results at any time.
        
        # Check if there are any results in history to generate insights from.
        if st.session_state.raw_df_history:
            latest_results = st.session_state.raw_df_history[-1]
            # Ensure the latest results are a non-empty DataFrame with player names
            if isinstance(latest_results, pd.DataFrame) and not latest_results.empty and 'full_name' in latest_results.columns:
                
                st.divider()
                st.subheader("On-Demand Analysis")

                # ---------------------- CHANGE 2.2: ADDITION START ---------------------
                # This renders the dropdown and button, giving the user control.
                player_list = latest_results['full_name'].tolist()
                st.selectbox(
                    "Select a player to analyze:",
                    options=player_list,
                    key="selected_player_for_note" # Links this widget to our session state variable
                )

                generate_button = st.button("Generate Analyst's Note")
                # ---------------------- CHANGE 2.2: ADDITION END -----------------------
                
                # ---------------------- CHANGE 2.3: ADDITION START ---------------------
                # This implements the on-click logic for the button.
                if generate_button:
                    with st.spinner(f"Generating note for {st.session_state.selected_player_for_note}..."):
                        # Retrieve all necessary context from the session state
                        note = self.agent.generate_on_demand_insight(
                            player_name=st.session_state.selected_player_for_note,
                            full_df=st.session_state.full_df,
                            active_archetype=st.session_state.active_archetype
                        )
                        # Store the generated note in the session state
                        st.session_state.current_analyst_note = note
                # ---------------------- CHANGE 2.3: ADDITION END -----------------------

                # ---------------------- CHANGE 2.4: ADDITION START ---------------------
                # This section displays the note if it exists in the session state.
                if st.session_state.current_analyst_note:
                    with st.container(border=True):
                        st.markdown(st.session_state.current_analyst_note)

    def run(self):
        """The main execution method that renders the entire UI."""
        self._initialize_session_state()
        self._render_sidebar()
        
        if st.session_state.data_loaded:
            self._render_chat() # This part will be enhanced in later sprints
        else:
            st.info("👋 Welcome to the 1stScout Demo! Please upload a CSV file or create a new logbook template to get started.")

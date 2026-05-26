# 3rd party & native imports
from pathlib import Path

import streamlit as st
from datetime import datetime

# Private / internal imports
from packethuffer.utils import *
from packethuffer.streamlitUtils import *

# Title & branding

st.set_page_config(
    page_title="PacketHuffer",
    page_icon="🛜",
)

st.title("PacketHuffer")

# Image path
parent_path = Path(__file__).parent
image_path = parent_path / "assets" / "packet-huffer.png"

st.image(image_path, width=400)

# Setup the Sidebar
st.sidebar.header("Configuration")

# Setup the option to select a config file
st.sidebar.subheader("Config File")
config_file = file_selector(folder_path=parent_path, file_extension=".yaml")

# Allow for either file upload or local file selection
file_tab1, file_tab2 = st.tabs(["Select Local Kismet Files", "Upload Kismet Files"])

# Local file selection
with file_tab1:
    st.write("Select .kismet files from the server")
    local_kismet_folder = st.text_input(
        "Folder path containing .kismet files", value="./"
    )
    local_db_files = file_selector(
        folder_path=local_kismet_folder, file_extension=".kismet", multiselect=True
    )

# Remote file upload
with file_tab2:
    st.write("Upload Kismet Files")
    remote_db_files = st.file_uploader(
        "Upload one or more .kismet files", type=["kismet"], accept_multiple_files=True
    )

# Stop if we have no files
if not remote_db_files and not local_db_files:
    st.warning("Please upload one or more Kismet files to continue.")
    st.stop()

# Setup PacketHuffer
huffer = initialize_huffer(config_file, local_db_files, remote_db_files)
kismet_network_data = huffer.get_enriched_network_data()

# Pull rules for filtering
rules = huffer.get_rules()

st.subheader("Kismet Network Data")

# Allow for users to filter network data by premade rule - or by custom query
filter_tab1, filter_tab2 = st.tabs(["Rule-Based Filtering", "Custom Query Filter"])

# Premade rule-based filtering
with filter_tab1:

    # Display the dataframe and allow filtering output based on rules
    all_rule_names = sorted([rule.name for rule in rules])

    allowed_filters = st.multiselect(
        "Include networks based on rules:", options=all_rule_names
    )

    disallowed_filters = st.multiselect(
        "Exclude networks based on rules:", options=all_rule_names
    )

    st.write(
        "Filtering operations are inclusive, selecting 2 rules will show/hide results matching either rule."
    )

    # Filter the dataframe based on selection
    if allowed_filters or disallowed_filters:

        allowed_guidance = []
        disallowed_guidance = []
        filtered_df = kismet_network_data

        # Build positive filters
        for allowed_rule in allowed_filters:
            # Map rule name to rule content
            rule_guidance = next(
                (rule.guidance for rule in rules if rule.name == allowed_rule), ""
            )
            allowed_guidance.append(rule_guidance)

        # Build negative filters
        for disallowed_rule in disallowed_filters:
            # Map rule name to rule content
            rule_guidance = next(
                (rule.guidance for rule in rules if rule.name == disallowed_rule),
                "",
            )
            disallowed_guidance.append(rule_guidance)

        # Filter the DF
        if allowed_filters:
            filtered_df = filtered_df[
                filtered_df["operator_guidance"].apply(
                    lambda x: isinstance(x, list)
                    and any(guidance in allowed_guidance for guidance in x)
                )
            ]

        if disallowed_filters:
            filtered_df = filtered_df[
                filtered_df["operator_guidance"].apply(
                    lambda x: not any(guidance in disallowed_guidance for guidance in x)
                )
            ]

    else:
        filtered_df = kismet_network_data

    # If we're filtering the data make that clear to the user
    if allowed_filters or disallowed_filters:
        st.write(
            f"Found {len(filtered_df)} matching networks out of {len(kismet_network_data)} total networks"
        )

    # Show the filtered dataframe
    st.dataframe(filtered_df)

# Custom Query Filtering
with filter_tab2:
    st.write(
        "Enter a custom pandas query to filter the networks. These are evaluated using `pandas.query()`, read [more info here](https://pandas.pydata.org/docs/reference/api/pandas.eval.html#pandas.eval)."
    )

    # Example queries
    example_queries = [
        "SSID.str.contains('Guest', case=False)",
        "crypt_string.str.contains('WEP')",
        "is_wpa3_transition == True",
        "num_associated_clients > 5",
        'channel == "6"',
    ]

    with st.expander("Example queries"):
        for query in example_queries:
            st.code(query)

    query_text = st.text_input(
        "Enter query:", placeholder="e.g., is_wpa2 == True and is_psk == True"
    )

    # Evaluate query if present
    if query_text:
        try:
            filtered_df = kismet_network_data.query(query_text)
            st.write(
                f"Found {len(filtered_df)} matching networks out of {len(kismet_network_data)} total networks"
            )
        except Exception as e:
            st.error(f"Error in query: {str(e)}")
            filtered_df = kismet_network_data

    st.dataframe(filtered_df)

# Allow for file download
datetime_stamp = f"{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"

st.subheader("File Downloads")
st.write(
    "These downloads will include the full network data, they do not respect any selected filtering options."
)

st.download_button(
    label="Download full network data as JSON",
    data=huffer.generate_json_output(),
    file_name=f"packethuffer_export_{datetime_stamp}.json",
    mime="text/json",
)

st.download_button(
    label="Download network inventory as XLSX",
    data=huffer.generate_xlsx_output(),
    file_name=f"packethuffer_export_{datetime_stamp}.xlsx",
    mime="text/xlsx",
)

# 3rd Party / Native imports
import logging
import os
import streamlit as st
from rich.logging import RichHandler

# Private/Internal imports
from packethuffer.packethuffer import PacketHuffer


@st.cache_resource
def initialize_huffer(
    config_file: str, local_files=None, remote_files=None
) -> PacketHuffer:
    """
    Configures and instantiates a PacketHuffer class for use in the Streamlit GUI
    Caches this object to avoid repetitive data processing
    """

    # Setup logging to streamlit CLI
    logging.basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )
    logger = logging.getLogger("PacketHuffer")

    huffer = PacketHuffer(logger, config_file)

    if local_files:
        huffer.load_data_from_local_dbs(local_files)
    else:
        huffer.load_data_from_streamlit_dbs(remote_files)

    huffer.run()
    return huffer


def file_selector(folder_path=".", file_extension=None, multiselect=False):
    """
    Takes in a local path and file extension
    Returns files with that extension for a streamlit selector
    If multiselect is True, returns a list of file paths, otherwise returns a single file path
    """
    # Get the list of files in the specified folder & filter out dirs
    filenames = os.listdir(folder_path)
    files = [f for f in filenames if os.path.isfile(os.path.join(folder_path, f))]

    # Filter by file extension if specified
    if file_extension:
        if not file_extension.startswith("."):
            file_extension = "." + file_extension
        files = [f for f in files if f.lower().endswith(file_extension.lower())]

    files.sort()

    # If no files match the criteria
    if not files:
        st.warning(f"No {file_extension} files found in {folder_path}")
        return [] if multiselect else None

    # Let the user select file(s) from the list
    if multiselect:
        # Create two columns for the selection options
        col1, col2 = st.columns([1, 3])

        # Add "Select All" checkbox in the first column
        with col1:
            select_all = st.checkbox(
                "Select All Files", key=f"select_all_{folder_path}_{file_extension}"
            )

        # Handle file selection in the second column
        with col2:
            if select_all:
                selected_filenames = files
                # Show the multiselect with all options pre-selected
                st.multiselect(
                    "Selected files:",
                    files,
                    default=files,
                    key=f"multi_{folder_path}_{file_extension}",
                )
            else:
                selected_filenames = st.multiselect(
                    "Select file(s):",
                    files,
                    key=f"multi_{folder_path}_{file_extension}",
                )

        # Display the count of selected files
        if selected_filenames:
            st.info(f"Selected {len(selected_filenames)} out of {len(files)} files")

        return [os.path.join(folder_path, filename) for filename in selected_filenames]
    else:
        selected_filename = st.sidebar.selectbox("Select a file", files)
        return os.path.join(folder_path, selected_filename)

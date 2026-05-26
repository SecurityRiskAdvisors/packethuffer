from pathlib import Path
import sys
import streamlit.web.cli as stcli


def main():
    """
    Wrapper script to launch the Streamlit PacketHuffer GUI
    """

    script_path = Path(__file__).parent / "streamlit.py"
    sys.argv = ["streamlit", "run", str(script_path)]
    stcli.main()


if __name__ == "__main__":
    main()

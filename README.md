# PacketHuffer

PacketHuffer is a [Kismet](https://www.kismetwireless.net/) data parser that makes it easier for operators to turn warwalking data into actionable intelligence. It parses one or more `.kismet` databases into a unified output that identifies interesting networks based on a series of configurable rules (ex. flag all networks without encryption).

PacketHuffer has both a CLI and a GUI, it can generate both JSON and XLSX output. The GUI allows for network data to be easily viewed and filtered by either preset rules, or custom queries.

## Installation

PacketHuffer has only been tested on Python `3.12.3`.

Use [poetry](https://python-poetry.org/), [pipx](https://pipx.pypa.io/stable/), or a similar tool to install PacketHuffer:

```bash
poetry install

pipx install .
```

Copy the Streamlit `config.toml` — this step is optional, but will provide a dark theme and resolve issues with upload limits in Streamlit:

```bash
mkdir ~/.streamlit
cp ./.streamlit/config.toml ~/.streamlit/config.toml
```

## Configuration

PacketHuffer can be configured using a `.yaml` file, see `/packethuffer/config.yaml` for the default configuration. The configuration file allows you to change the format of the XLSX output, or to modify the rules used to identify interesting networks.

Network identification rules are evaluated using the pandas `df.query()` and `df.eval()` functions, which use basic python expressions. Read more about the syntax [here](https://pandas.pydata.org/docs/reference/api/pandas.eval.html#pandas.eval).

If you'd like to build a rule but the PacketHuffer dataframe lacks needed information, you may need to modify `build_network_dataframe()` within `/packethuffer/utils.py` to pull in additional data from the Kismet device information (this is a one-time modification, make a PR after).

## Usage

To run PacketHuffer with the GUI in your web browser:

```bash
poetry run packethuffer-gui

# or

packethuffer-gui
```

To run PacketHuffer in the CLI:

```bash
poetry run packethuffer

# or

packethuffer
```

Basic usage (pipx):

```bash
# Help
packethuffer -h

# Process X kismet files
packethuffer ~/path/to/kismet/files/*.kismet

# Process kismet files and provide excel output, with verbose logging
packethuffer ~/path/to/kismet/files/*.kismet -i -v
```

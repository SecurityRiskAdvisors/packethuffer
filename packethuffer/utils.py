import random
import sqlite3
import string
import tempfile
from pandas import DataFrame
import pandas as pd
import json
import xlsxwriter
import yaml
import io

from packethuffer.config import Rule


HOTSPOT_MANUFACTURERS = ["Apple, Inc.", "Samsung Electronics Co.,Ltd"]


def identify_locally_administered_mac(devmac: str) -> bool:
    """
    Returns true if supplied MAC address is in the range for locally administered MAC address
    """
    char = devmac[1]

    local_ranges = ["2", "6", "A", "E"]

    return True if char in local_ranges else False


def anonymize_dataframe(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """
    Anonymize a dataframe by randomizing the content of specified columns.
    """

    for col in columns:
        if col not in df:
            continue

        df[col] = [
            "".join(random.choices(string.ascii_letters + string.digits, k=10))
            for _ in range(len(df))
        ]

    return df


def load_table_from_db(file: str, table_name: str) -> DataFrame:
    """
    Reads a single table from a sqlite DB and returns it as a dataframe
    """
    conn = sqlite3.connect(file)
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df


def load_table_from_streamlit_db(file, table_name: str) -> DataFrame:
    """
    Takes a sqlite DB uploaded to streamlit and returns a single table from the database as a dataframe
    """

    # Save the file in a tempfile
    with tempfile.NamedTemporaryFile(delete=True) as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name

        conn = sqlite3.connect(tmp_path)
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        return df


def generate_network_inventory(
    df: DataFrame, inventory_headers: list[str], inventory_data: list[str]
):
    """
    Generates an Excel inventory of wireless networks from a DataFrame
    Returns bytes containing the Excel file, ready for Streamlit download button
    """

    # Hold the excel file in memory and setup the workbook
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})

    # Determine the last column letter for formatting
    last_col = xlsxwriter.utility.xl_col_to_name(len(inventory_headers) - 1)
    excel_headers = [{"header": header} for header in inventory_headers]

    # Create a new sheet in the workbook
    worksheet = workbook.add_worksheet(name="Wireless Inventory")

    # Write the header row to the worksheet
    for col_idx, col in enumerate(inventory_headers):
        worksheet.write(0, col_idx, col)

    # Prepare rows for Excel - pull out the data from the df
    excel_rows = []
    for _, row in df.iterrows():
        excel_row = []
        for header in inventory_data:
            excel_row.append(row.get(header, ""))
        excel_rows.append(excel_row)

    # Write the data rows
    for row_idx, row in enumerate(excel_rows, start=1):
        for col_idx, value in enumerate(row):
            worksheet.write(row_idx, col_idx, value)

    # Define table range and add table formatting
    table_range = f"A1:{last_col}{len(excel_rows) + 1}"
    worksheet.add_table(table_range, {"columns": excel_headers})

    workbook.close()

    # Get the bytes value from the BytesIO object
    excel_bytes = output.getvalue()
    output.close()

    return excel_bytes


def _apply_rule(df: DataFrame, rule: Rule) -> DataFrame:
    """
    Apply a single rule to the dataframe.
    """
    try:
        # Use pandas eval to evaluate the condition on the dataframe
        mask = df.eval(rule.condition)

        # For rows where condition is True, add the guidance
        df.loc[mask, "operator_guidance"] = df.loc[mask, "operator_guidance"].apply(
            lambda guidance_list: guidance_list + [rule.guidance]
        )
    except Exception as e:
        print(f"Error applying rule {rule.name}: {e}")

    return df


def load_yaml(config_file: str) -> dict:
    """
    Load content from a yaml file, takes in a path to a yaml file
    """
    with open(config_file, "r") as file:
        config = yaml.safe_load(file)
        return config


# TODO: insert the operator guidance at index 2
def identify_interesting_networks(df: DataFrame, rules: dict) -> DataFrame:
    """
    Takes in our enriched/metatable kismet network dataframe and runs a series of checks to identify interesting networks for operators.
    Returns a dataframe with a new operator guidance field.
    """

    result_df = df.copy()

    if rules is None:
        print("Error: no rules found")
        return

    # Initialize operator_guidance as an empty list for each row
    result_df["operator_guidance"] = result_df.apply(lambda _: [], axis=1)

    # Apply each rule to the dataframe to identify networks and add guidance
    for rule in rules:
        # Apply the rule condition and add guidance if condition is met
        result_df = _apply_rule(result_df, rule)

    return result_df


def build_network_dataframe(df: DataFrame) -> DataFrame:
    """
    Takes in a dataframe containing Kismet access points from the devices table. Builds a new dataframe with only the information we need from the device field
    """

    # Pair it down to just APs
    aps = df[df["type"] == "Wi-Fi AP"]

    # Create our network "metatable" - this is going to store only the information that we care about when running our checks
    networks_list = []

    # Enrich the data with fields we want to pull out of the kismet device field
    for _, ap in aps.iterrows():  # Use iterrows() to iterate through DataFrame rows
        try:
            device_json = ap["device"]

            # Pull out each network advertised by the AP
            advertised_networks = device_json["dot11.device"].get(
                "dot11.device.advertised_ssid_map", []
            )

            # Pull out each network responded by the AP (for hidden network identification)
            responded_networks = device_json["dot11.device"].get(
                "dot11.device.responded_ssid_map", []
            )

            for network_data in advertised_networks:
                advertised_ssid = network_data.get("dot11.advertisedssid.ssid", "")

                if len(responded_networks) > 0:
                    responded_ssid = responded_networks[0].get(
                        "dot11.advertisedssid.ssid", ""
                    )
                else:
                    responded_ssid = ""

                if advertised_ssid == "":
                    ssid = responded_ssid
                else:
                    ssid = advertised_ssid

                crypt_string = network_data.get(
                    "dot11.advertisedssid.crypt_string", ""
                ).lower()

                # Check for various security types
                is_wpa2 = any(
                    wpa2_type in crypt_string for wpa2_type in ["wpa2", "rsn", "psk2"]
                )
                is_psk = "psk" in crypt_string
                is_enterprise = any(
                    enterprise_indicator in crypt_string
                    for enterprise_indicator in ["eap", "802.1x", "enterprise"]
                )
                is_wpa3_transition = (
                    ("wpa3" in crypt_string and "wpa2" in crypt_string)
                    or "transition" in crypt_string
                    or ("sae" in crypt_string and "psk" in crypt_string)
                )
                is_wep = "wep" in crypt_string
                is_eap = any(
                    eap_indicator in crypt_string
                    for eap_indicator in [
                        "eap",
                        "802.1x",
                        "enterprise",
                        "leap",
                        "peap",
                        "ttls",
                        "tls",
                    ]
                )
                is_wpa = "wpa" in crypt_string

                # Try to determine MFP status
                mfp_status = "Disabled"

                mfp_required = network_data.get(
                    "dot11.advertisedssid.wpa_mfp_required", 0
                )
                mfp_supported = network_data.get(
                    "dot11.advertisedssid.wpa_mfp_supported", 0
                )

                if mfp_required == 1:
                    mfp_status = "Required"
                elif mfp_supported == 1:
                    mfp_status = "Optional"

                channel = network_data.get("dot11.advertisedssid.channel")
                advertised_connected_clients = device_json["dot11.device"].get(
                    "dot11.device.num_associated_clients"
                )

                # Device manufacturer / mac based info
                manufacturer = device_json["kismet.device.base.manuf"]
                mac = ap["devmac"]

                potential_hotspot = (
                    True if manufacturer in HOTSPOT_MANUFACTURERS else False
                )

                # Create a dictionary for this network
                network_dict = {
                    "SSID": ssid,
                    "crypt_string": crypt_string,
                    "channel": channel,
                    "num_associated_clients": advertised_connected_clients,
                    "mfp_status": mfp_status,
                    "is_wpa2": is_wpa2,
                    "is_psk": is_psk,
                    "is_enterprise": is_enterprise,
                    "is_wpa3_transition": is_wpa3_transition,
                    "is_wep": is_wep,
                    "is_wpa": is_wpa,
                    "is_eap": is_eap,
                    "devmac": mac,
                    "dev_manufacturer": manufacturer,
                    "locally_administered_mac": identify_locally_administered_mac(mac),
                    "hotspot": potential_hotspot,
                    "advertised_SSID": advertised_ssid,
                    "responded_SSID": responded_ssid,
                    "source_db": ap["source_db"],
                    "last_time": ap["last_time"],
                    "full_device_details": ap["device"],
                }

                networks_list.append(network_dict)
        except Exception as e:
            # Skip this AP if there's an error processing it
            print(f"Error processing AP {ap.get('devmac', 'unknown')}: {e}")
            continue

    # Create the final DataFrame from the list of dictionaries
    networks = pd.DataFrame(networks_list)

    # Deduplicate devices by SSID and merge the source_db field
    unique_networks = deduplicate_devices_by_field(
        networks,
        "SSID",
        {
            "source_db": lambda x: sorted(set(x)),
            "channel": lambda x: sorted(set(x)),
            "devmac": lambda x: sorted(set(x)),
            "num_associated_clients": lambda x: x.sum(),
        },
    )

    return unique_networks


def deduplicate_devices_by_field(
    df: DataFrame, field: str, combine_columns: dict[str, callable] | None = None
) -> DataFrame:
    """
    Takes in a dataframe containing Kismet devices from the devices table, deduplicates by specified field, and returns the updated dataframe.
    Keeps the device entry that was last seen.
    Merges the source_db field with unique values.
    """

    # Sort by 'last_time' in descending order and keep the last seen data point
    df_sorted = df.sort_values("last_time", ascending=False)
    df_deduped = df_sorted.drop_duplicates(subset=[field])

    # Stop here if we're not combining anything
    if not combine_columns:
        return df_deduped

    # Run combination rules
    agg_dict = {col: func for col, func in combine_columns.items()}
    combined = df.groupby(field).agg(agg_dict).reset_index()
    df_deduped = df_deduped.drop(columns=combine_columns.keys(), errors="ignore")
    result = pd.merge(df_deduped, combined, on=field, how="left")

    return result


def _blob_to_dict(blob) -> dict:
    """
    Transfers a kismet device blob to a dict
    """
    if blob is None:
        return None
    else:
        return json.loads(blob.decode("utf-8"))


def process_kismet_device_field(df: DataFrame):
    """
    Takes in a dataframe containing Kismet devices from the devices table, processes the device BLOB, and returns the updated dataframe.
    """
    df["device"] = df["device"].apply(_blob_to_dict)
    return df

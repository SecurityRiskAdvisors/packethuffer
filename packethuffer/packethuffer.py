from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from pandas import DataFrame

# Internal / private imports
from packethuffer.config import Rule, PacketHufferConfig
from packethuffer.utils import *


@dataclass
class PacketHuffer:

    logger: Logger
    config_file: str

    def __post_init__(self):
        # Load YAML config file
        self.logger.info("Loading config from YAML")
        raw_config = load_yaml(self.config_file)
        config = PacketHufferConfig.model_validate(raw_config)

        self.rules = config.rules
        self.xlsx_format = config.xlsx_format
        self.metrics = {}

    def get_rules(self) -> list[Rule]:
        """
        Returns the list of rules used for filtering/network ID
        """

        return self.rules

    def anonymize_data(self) -> DataFrame:
        """
        Used to anonymize data for demo purposes
        """
        self.logger.info("Anonymizing data.")

        self.enriched_kismet_network_data = anonymize_dataframe(
            self.enriched_kismet_network_data,
            ["SSID", "devmac", "advertised_SSID", "responded_SSID"],
        )

    def get_enriched_network_data(self) -> DataFrame:
        """
        Returns the DataFrame of final PacketHuffer data
        """

        return self.enriched_kismet_network_data

    def run(self) -> None:
        """
        Runs the PacketHuffer on supplied network data
        """

        self.logger.info("Huffing some packets...")
        # Pull out network data
        self.kismet_network_data = build_network_dataframe(self.full_kismet_device_data)

        # Enrich the data - build our metatable with the information we care about, and run a series of checks
        self.enriched_kismet_network_data = identify_interesting_networks(
            self.kismet_network_data, self.rules
        )

        # Save some metrics for the summary
        self.metrics["num_networks"] = len(self.kismet_network_data)
        self.metrics["num_rules_processed"] = len(self.rules)

        return

    def generate_json_output(self) -> bytes:
        """
        Generates a JSON export of network data
        """

        self.logger.info("Generating JSON output.")
        return self.enriched_kismet_network_data.to_json().encode("utf-8")

    def generate_xlsx_output(self) -> bytes:
        """
        Generates an Excel export of network data
        """

        self.logger.info("Generating XLSX output.")
        return generate_network_inventory(
            self.enriched_kismet_network_data,
            self.xlsx_format.column_names,
            self.xlsx_format.column_data,
        )

    def summarize_data(self):
        """
        Generates a summary of data processed for CLI logging
        """

        summary = f"""
# PacketHuffer Result Summary

## Data processed

* Processed {self.metrics["dbs_processed"]} files
* Kismet files contained {self.metrics["total_records"]} total records
* Kismet files contained {self.metrics["deduplicated_records"]} unique records (by MAC)

## Network Data

* Identified {self.metrics["num_networks"]} unique networks
* Processed {self.metrics["num_rules_processed"]} rules to identify interesting networks
"""

        return summary

    def _merge_dbs(self, dfs: list[DataFrame]) -> None:
        """
        Merges the contents of multiple Kismet databases and deduplicates records by MAC
        """

        self.logger.info("Merging & processing databases.")
        merged_data = deduplicate_devices_by_field(
            process_kismet_device_field(pd.concat(dfs, ignore_index=True)), "devmac"
        )

        self.full_kismet_device_data = merged_data

        # Save some metrics for the summary
        self.metrics["deduplicated_records"] = len(merged_data)

    def load_data_from_streamlit_dbs(self, files) -> None:
        """
        Loads the content of Kismet databases from streamlit to a single DataFrame
        """

        dfs = []
        num_records = 0

        for f in files:
            self.logger.info(f"Loading database: {f.name}")
            # Pull the devices table from each DB into a dataframe
            df = load_table_from_streamlit_db(f, "devices")

            # Add a column with the database it came from
            df["source_db"] = f.name
            dfs.append(df)
            num_records += len(df)

        self._merge_dbs(dfs)

        # Save some metrics for the summary
        self.metrics["dbs_processed"] = len(files)
        self.metrics["total_records"] = num_records

    def load_data_from_local_dbs(self, files: list[str]) -> None:
        """
        Loads the content of Kismet databases from local files to a single DataFrame
        """

        dfs = []

        num_records = 0

        for file in files:
            file_name = Path(file).name
            self.logger.info(f"Loading database: {file_name}")
            df = load_table_from_db(file, "devices")
            df["source_db"] = file_name  # Parse out just the filename for the source DB
            dfs.append(df)
            num_records += len(df)

        self._merge_dbs(dfs)

        # Save some metrics for the summary
        self.metrics["dbs_processed"] = len(files)
        self.metrics["total_records"] = num_records

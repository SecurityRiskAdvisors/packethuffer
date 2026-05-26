import argparse
from dataclasses import dataclass
from logging import Logger
from datetime import datetime
from pathlib import Path


@dataclass
class Args:
    logger: Logger

    def __post_init__(self):
        self.parser = argparse.ArgumentParser()
        self._setup_arguments()

    def run(self):
        """
        Parse CLI arguments
        """

        self.logger.info("Parsing CLI arguments")
        self.args = self.parser.parse_args()
        return self.args

    def _setup_arguments(self):

        # Save a timestamp for filenames
        datetime_stamp = f"{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"

        self.parser.add_argument(
            "files",
            nargs="+",
            help="Kismet files to process (can use wildcards)",
        )

        self.parser.add_argument(
            "--inventory",
            "-i",
            action="store_true",
            help="Generate an xlsx inventory of identified wireless networks",
        )

        self.parser.add_argument(
            "--json-out",
            "-o",
            help="JSON output file path",
            default=f"./packethuffer_export_{datetime_stamp}.json",
        )

        self.parser.add_argument(
            "--inventory-out",
            "-io",
            help="Inventory output file path",
            default=f"./packethuffer_export_{datetime_stamp}.xlsx",
        )

        self.parser.add_argument(
            "--config",
            "-c",
            help="Path to a YAML config file.",
            default=(Path(__file__).parent / "config.yaml"),
        )

        self.parser.add_argument(
            "--verbose", "-v", action="store_true", help="Increase logging verbosity"
        )

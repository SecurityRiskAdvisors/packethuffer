# 3rd party & native imports
import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.markdown import Markdown
from pathlib import Path

# internal / private imports
from packethuffer.args import Args
from packethuffer.packethuffer import PacketHuffer
from packethuffer.utils import *


def main():
    """
    PacketHuffer CLI Script
    """

    # Setup logging
    logging.basicConfig(
        level="WARNING",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )
    logger = logging.getLogger("PacketHuffer")
    console = Console()

    # Pull in arguments - parse & validate
    logger.info("Loading CLI arguments")
    args_parser = Args(logger)
    args = args_parser.run()

    # Increase logging verbosity if selected
    if args.verbose:
        logger.setLevel("DEBUG")

    # Very important (+5 efficiency)
    banner = r"""   ___           __       __  __ __     ______       
  / _ \___ _____/ /_____ / /_/ // /_ __/ _/ _/__ ____
 / ___/ _ `/ __/  '_/ -_) __/ _  / // / _/ _/ -_) __/
/_/   \_,_/\__/_/\_\\__/\__/_//_/\_,_/_//_/ \__/_/   
                                                     """
    console.print(banner, style="bold blue")

    # Setup Packethuffer
    huffer = PacketHuffer(logger, args.config)
    huffer.load_data_from_local_dbs(args.files)

    console.print("Huffin some packets...")
    huffer.run()

    # Display a CLI summary of interesting info
    console.print(Markdown(huffer.summarize_data()))

    # Build excel inventory if requested
    if args.inventory:
        xlsx_output = huffer.generate_xlsx_output()
        logger.info(f"Saving XLSX output to {args.inventory_out}")
        Path(args.inventory_out).write_bytes(xlsx_output)
        console.print(f"Saved XLSX output to {args.inventory_out}")

    # Save output to JSON
    json_output = huffer.generate_json_output()
    logger.info(f"Saving JSON output to {args.json_out}")
    Path(args.json_out).write_bytes(json_output)
    console.print(f"Saved JSON output to {args.json_out}")

    console.print(f"All done huffin.")


if __name__ == "__main__":
    main()

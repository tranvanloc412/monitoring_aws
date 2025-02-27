import argparse
import logging
from typing import NamedTuple, Optional


class CliArgs(NamedTuple):
    lz: str
    action: str
    dry_run: bool
    change_request: Optional[str]


class CliParser:
    @staticmethod
    def parse_arguments() -> CliArgs:
        parser = argparse.ArgumentParser(description="CMS Monitoring Alarm Management")
        parser.add_argument(
            "--lz-shortname",
            "-lz",
            type=str,
            required=True,
            help="Specify the landing zone name (e.g., cmsnonprod, cmsprod).",
        )
        parser.add_argument(
            "--action",
            "-a",
            type=str,
            choices=["create", "scan", "delete"],
            required=True,
            help="Action to perform: 'create', 'scan', or 'delete'.",
        )
        parser.add_argument(
            "--dry-run",
            "-dr",
            action="store_true",
            help="Perform a dry run without applying any changes.",
        )
        parser.add_argument(
            "--change-request",
            "-cr",
            type=str,
            help=(
                "Change request number for logging purposes. "
                "Required for production landing zones when creating alarms."
            ),
        )
        args = parser.parse_args()
        return CliArgs(
            lz=args.lz_shortname,
            action=args.action,
            dry_run=args.dry_run,
            change_request=args.change_request,
        )

    @staticmethod
    def is_production_lz(lz_name: str) -> bool:
        """
        Check if the provided landing zone name corresponds to a production environment.
        """
        lz_lower = lz_name.lower()
        return (
            "prod" in lz_lower
            and "nonprod" not in lz_lower
            and "preprod" not in lz_lower
        )

    @staticmethod
    def validate_production_lz(args: CliArgs, logger: logging.Logger) -> None:
        """
        Validate that a change request number is provided for production landing zones
        when the action is 'create'. Raises a ValueError if validation fails.
        """
        if CliParser.is_production_lz(args.lz) and args.action == "create":
            if not args.change_request:
                error_message = f"Change request number is required for production landing zone '{args.lz}' when creating alarms."
                logger.error(error_message)
                raise ValueError(error_message)

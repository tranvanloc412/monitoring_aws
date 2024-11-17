import argparse
import logging
from typing import NamedTuple


class CliArgs(NamedTuple):
    lz: str
    action: str
    dry_run: bool
    change_request: str | None


class CliParser:
    @staticmethod
    def parse_arguments() -> CliArgs:
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(description="CMS Monitoring Alarm Management")
        parser.add_argument(
            "--landing-zone",
            "-lz",
            type=str,
            default="all",
            help="Specific landing zone to process (e.g., lz250prod, cmsprod) or 'all'",
        )
        parser.add_argument(
            "--action",
            "-a",
            type=str,
            choices=["create", "scan", "delete"],
            required=True,
            help="Action to perform: 'create', 'scan', or 'delete'",
        )
        parser.add_argument(
            "--dry-run",
            "-dr",
            action="store_true",
            help="Dry run the action",
        )
        parser.add_argument(
            "--change-request",
            "-cr",
            type=str,
            help="Change request number for logging (required for production landing zones)",
        )
        args = parser.parse_args()
        return CliArgs(
            lz=args.landing_zone,
            action=args.action,
            dry_run=args.dry_run,
            change_request=args.change_request,
        )

    @staticmethod
    def is_production_lz(lz_name: str) -> bool:
        """Check if the landing zone is a production environment."""
        lz_name_lower = lz_name.lower()
        return (
            "prod" in lz_name_lower
            and "nonprod" not in lz_name_lower
            and "preprod" not in lz_name_lower
        )

    @staticmethod
    def validate_production_lz(args: CliArgs, logger: logging.Logger) -> None:
        """Validate if a change request number is required for production landing zones."""
        if CliParser.is_production_lz(args.lz) and args.action == "create":
            if not args.change_request:
                error_message = (
                    "Change request number is required for production landing zones."
                )
                logger.error(error_message)
                raise ValueError(error_message)

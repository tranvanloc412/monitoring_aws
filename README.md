# CMS Monitoring Alarm Management

This script is designed to manage alarms for AWS landing zones in a CMS (Cloud Management System) environment. It provides functionality to create, scan, and delete alarms for specified landing zones.

## Features

- **Create Alarms**: Deploys alarm definitions for specified landing zones.
- **Scan Resources**: Scans resources in the landing zone to ensure they are monitored.
- **Delete Alarms**: Removes alarms from the specified landing zones.

## Prerequisites

- Python 3.10 or later
- AWS credentials configured for access to the landing zones.
- Required Python packages (see `requirements.txt` if available).

## Configuration

Ensure the following configuration files are present in the specified paths:

- Landing Zone Configuration (`LZ_CONFIG`)
- Alarm Settings (`ALARM_SETTINGS`)
- Category Configurations (`CATEGORY_CONFIGS`)
- Custom Settings (`CUSTOM_SETTINGS`)

## Setup Instructions

For detailed setup instructions, including creating a virtual environment and installing dependencies, please refer to the [Setup Guide](docs/setup.md).

## Usage

Run the script using the command line with the following options:

### Arguments

- `--lz`, `-l`: Specify the landing zone to process (e.g., `lz250prod`, `cmsprod`) or use `all` to process all landing zones.
- `--action`, `-a`: Action to perform. Choices are `create`, `scan`, or `delete`.
- `--change-request`, `-cr`: Change request number for logging. Required for production landing zones when creating alarms.

## Example

To create alarms for a specific landing zone:

```bash
python main.py --lz lz250prod --action create --change-request CR12345
```

To scan resources for all landing zones:

```bash
python main.py --lz all --action scan
```

## Logging

The script uses Python's logging module to log information and errors. Ensure the `LOG_FORMAT` is configured in the `constants` module.

## Error Handling

The script will log errors and raise exceptions if configuration files are missing or if there are issues during the setup or processing of landing zones.


## Contact

For questions or feedback, please contact the CMS team.

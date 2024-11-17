# CMS Monitoring Alarm Management

This script is designed to manage alarms for AWS landing zones in a CMS (Cloud Management System) environment. It provides functionality to create, scan, and delete alarms for specified landing zones based on catergory configurations.

## Features

- **Create Alarms**: Deploys alarm definitions for specified landing zones.
- **Scan Resources**: Scans resources in the landing zone to ensure they are monitored.
- **Delete Alarms**: Removes alarms from the specified landing zones.
- **Dry Run Mode**: Simulates actions without making actual changes.

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

## Configuration Files

### Landing Zone Configuration (`configs/landing_zone_configs.yml`)

Defines the AWS account structure and categorization:

- `landing_zone`: Identifier for the landing zone
- `environments`: Maps environment types (prod/nonprod) to AWS account IDs
- `app_id`: Application identifier
- `cost_centre`: Cost center code
- `category`: Monitoring category (e.g., CAT_A, CAT_B, CAT_C, CAT_D) that determines alarm thresholds

### Category Configuration (`configs/category_configs.yml`)

Defines monitoring categories and their thresholds:

- `description`: Category description
- `sns_topic_arns`: List of SNS topics for alarm notifications
- `thresholds`: Resource-specific monitoring thresholds
  - Organized by resource type (EC2, RDS, etc.)
  - Defines specific metric thresholds (e.g., CPU, memory, disk space)

### Alarm Settings (`configs/alarm_settings.yml`)

Defines the CloudWatch alarm configurations for each resource type:

- Metric definitions including:
  - `namespace`: AWS namespace for the metric
  - `statistic`: Statistical method (e.g., Average)
  - `comparison_operator`: Threshold comparison type
  - `unit`: Measurement unit
  - `period`: Monitoring interval in seconds
  - `evaluation_periods`: Number of periods before triggering

### Custom Settings (`configs/custom_settings.yml`)

Provides override configurations and special cases:

- `disabled_alarms`: Specify alarms to disable for specific environments
- `sns_mappings`: Custom SNS topic mappings for specific metrics
  - Can override default SNS topics based on category
  - Supports different topics for different severity levels

## Configuration Examples

### Landing Zone Example

```yaml
- landing_zone: cms
  environments:
    nonprod: 891377130283
    prod:
  app_id: SPL-529
  category: CAT_A
```

### Category Threshold Example

```yaml
CAT_A:
  description: "Most Critical Systems"
  thresholds:
    EC2:
      CPUUtilization: 70
      mem_used_percent: 75
```

### Alarm Setting Example

```yaml
EC2:
  - metric:
      name: CPUUtilization
      namespace: "AWS/EC2"
    statistic: "Average"
    period: 300
    evaluation_periods: 3
```

## Documentation

For detailed information about this project, please refer to:

- [Architecture Documentation](docs/architecture.md) - Detailed technical design and component overview
- [Project Documentation](docs/projects.md) - Project specifications and requirements
- [Metrics and Thresholds](https://docs.google.com/spreadsheets/d/1868686868686868686868686868686868686868/edit?gid=0) - Monitor Metric and Threshold Details for Alarms
- [Test Cases](docs/test_cases.md) - Test cases for the script

## Setup Instructions

For detailed setup instructions, including creating a virtual environment and installing dependencies, please refer to the [Setup Guide](docs/setup.md).

## Usage

Run the script using the command line with the following options:

### Arguments

- `--lz`, `-l`: Specify the landing zone to process (e.g., `lz250prod`, `cmsprod`) or use `all` to process all landing zones.
- `--action`, `-a`: Action to perform. Choices are `create`, `scan`, or `delete`.
- `--change-request`, `-cr`: Change request number for logging. Required for production landing zones when creating alarms.
- `--dry-run`: Simulate the action without making actual changes. Shows what would happen during execution.

### Examples

Create alarms for a specific landing zone:

nonprod

``` bash
python3 main.py --lz cmsnonprod --action create
```

prod

```bash
python3 main.py --lz lz250prod --action create --change-request CR12345
```

Scan resources for all landing zones:

```bash
python3 main.py --lz all --action scan
```

Simulate alarm creation (dry run):

```bash
python3 main.py --lz lz250prod --action create --change-request CR12345 --dry-run
```

## Logging

The script uses Python's logging module to provide detailed execution information:

- Info level: Shows progress and successful operations.
- Warning level: Indicates potential issues.
- Error level: Reports execution failures.
- Dry run messages are clearly marked with `[DRY RUN]` prefix.

## Error Handling

The script includes comprehensive error handling:

- Validates configuration files before execution.
- Checks AWS session creation.
- Verifies landing zone existence.
- Requires change request numbers for production changes.
- Logs detailed error messages for troubleshooting.

## Future Improvements

- Update logging solution for audit trail
- Update testing solution: add unit test cases, functional test cases and standardised test data
- Use NAB managed docker image to containerise the repository
- Update contribution guide and CI pipeline
- Update solutions for custom alarms

## Contact

For questions or feedback, please contact the CMS AWS team.

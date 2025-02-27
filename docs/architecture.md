# Architecture Overview

## Purpose

Develop a scalable, maintainable, and extensible Python CLI tool that automates the creation, deletion, and scanning of AWS CloudWatch alerts across multiple AWS accounts based on resource categories and predefined thresholds.

## Key Requirements

- **Language:** Python 3.10 or higher
- **AWS SDK:** Boto3
- **Execution Environment:** Engineer's laptops or CMS jump boxes with access to AWS APIs
- **Deployment:** Source code repository (GitHub)
- **Logging:** Audit logs stored securely in an S3 bucket
- **Scalability:** Capable of handling 200+ AWS accounts
- **Extensibility:** Easy to add new resource types and functionalities in the future

## High-Level Design

```mermaid
flowchart TD
    A["Start\: Execute CLI Command"] --> B["Load Config & Setup Logging"]
    B --> C[Parse CLI Arguments]
    C --> D{Action: create or scan?}
    D -- "create" --> E[Assume Role in Target Landing Zone]
    D -- "scan" --> F[Initiate Parallel Scanning of Landing Zones]
    E --> G[Initialize Resource Plugins]
    F --> G
    G --> H[Discover AWS Resources via Plugins EC2, RDS, ALB, NLB, FSx, EFS]
    H --> I[Filter Resources by Tag: managed_by=CMS]
    I --> J[Determine Resource Category via Config Mapping]
    J --> K{Category}
    K -- "CAT_A" --> L[Invoke Strict Alert Plugin High SNS]
    K -- "CAT_B" --> M[Invoke Moderate Alert Plugin Medium SNS]
    K -- "CAT_C" --> N[Invoke Basic Alert Plugin Low SNS]
    K -- "CAT_D" --> O[Skip Alert Creation]
    L --> P[Log & Audit Alert Creation]
    M --> P
    N --> P
    O --> P
    P --> Q[Output Execution Summary]
    Q --> R[End Process]

    %% Error Handling Nodes
    B --- S[Global Error Handler Config, Logging]
    H --- T[Resource Discovery Error Handler]
    L --- U[Alert Creation Error Handler]
    M --- U
    N --- U
    T --> Q
    U --> Q
```

### Core Components

1. **Main Application (`main.py`):**

   - Entry point that initializes the application
   - Parses command-line arguments
   - Orchestrates the workflow based on user inputs
   - Handles error management and graceful shutdowns

2. **CLI Parser (`cli_parser.py`):**

   - Handles all command-line interactions
   - Validates inputs and argument combinations
   - Provides help messages and usage examples
   - Supports subcommands for different operations

3. **AWS Connection Manager (`aws_manager/core/session.py`):**

   - Manages AWS sessions and credentials
   - Handles role assumptions across accounts
   - Implements connection pooling and reuse
   - Provides retry logic for AWS API calls

4. **Resource Manager (`aws_manager/core/resources.py`):**

   - Discovers resources across AWS accounts
   - Filters resources based on tags and categories
   - Implements caching for resource lookups
   - Supports pagination for large resource sets

5. **Alarm Manager (`aws_manager/monitoring/alarm_manager.py`):**

   - Creates and deletes CloudWatch alarms
   - Manages alarm configurations and thresholds
   - Performs alarm health checks and validation
   - Supports bulk operations for efficiency

6. **Configuration Manager (`aws_manager/monitoring/alarm_config_manager.py`):**

   - Loads and validates YAML configurations
   - Handles landing zone configurations (`configs/landing_zone_configs.yml`)
   - Manages alarm settings (`configs/alarm_settings.yml`)
   - Manages category configurations (`configs/category_configs.yml`)
   - Manages default and custom settings (`configs/custom_settings.yml`)

7. **Logger (`logger.py`):**

   - Implements structured logging
   - Handles local and S3 log storage
   - Provides audit trail capabilities
   - Supports different log levels and formats

8. **Utilities (`utils.py`):**
   - Common helper functions
   - Reusable AWS utility functions
   - Date/time handling utilities
   - Input/output formatting helpers

### Codebase Structure

```plaintext
.
├── README.md
├── aws_manager
│   ├── __init__.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── landing_zone.py
│   │   ├── resources.py
│   │   └── session.py
│   └── monitoring
│       ├── __init__.py
│       ├── alarm_config.py
│       ├── alarm_config_manager.py
│       ├── alarm_manager.py
│       ├── constants.py
│       └── metric_config.py
├── cli_parser.py
├── configs
│   ├── alarm_settings.yml
│   ├── category_configs.yml
│   ├── custom_settings.yml
│   └── landing_zone_configs.yml
├── constants.py
├── docs
│   ├── architecture.md
│   ├── projects.md
│   └── setup.md
├── logger.py
├── main.py
├── requirements.txt
├── tests
│   ├── __init__.py
│   ├── test_iam.py
│   └── test_landing_zone.py
└── utils.py
```

### Application Flow Sequence

```mermaid
sequenceDiagram
    participant User
    participant Main
    participant CliParser
    participant LoggerSetup
    participant LandingZoneManager
    participant SessionManager
    participant ResourceScanner
    participant AlarmManager

    User->>Main: Execute script
    Main->>CliParser: parse_arguments()
    Main->>LoggerSetup: get_logger()

    Main->>CliParser: validate_production_lz()
    Main->>LandingZoneManager: load_lz_config()

    alt args.lz == "all"
        Main->>LandingZoneManager: get_all_landing_zones()
    else
        Main->>LandingZoneManager: get_landing_zone(args.lz)
    end

    loop For each landing zone
        Main->>SessionManager: get_or_create_session()
        Main->>ResourceScanner: get_managed_resources()
        Main->>AlarmManager: initialize

        alt args.dry_run
            Main->>AlarmManager: dry_run operations
        else args.action == "create"
            Main->>AlarmManager: create_all_alarm_definitions()
            Main->>AlarmManager: deploy_alarms()
        else args.action == "scan"
            Main->>AlarmManager: scan_alarms()
        else args.action == "delete"
            Main->>AlarmManager: delete_alarms()
        end
    end
```

### Alarm Manager Flow Sequence

```mermaid
sequenceDiagram
    participant Client
    participant AlarmManager
    participant AlarmConfigManager
    participant AWS CloudWatch
    participant ThreadPool

    Client->>AlarmManager: __init__(landing_zone, aws_session, ...)
    AlarmManager->>AlarmConfigManager: load_configs()
    AlarmManager->>AlarmManager: _load_states()

    Note over AlarmManager: Initialize configurations<br/>and scan existing alarms

    Client->>AlarmManager: create_all_alarm_definitions()
    activate AlarmManager
    AlarmManager->>ThreadPool: Create thread pool
    loop For each resource
        ThreadPool->>AlarmManager: _create_alarm_definitions(resource)
        alt is CWAgent namespace
            AlarmManager->>AlarmManager: _create_cwagent_alarm_definitions()
        else other namespace
            AlarmManager->>AlarmManager: _create_single_alarm_definition()
        end
    end
    AlarmManager-->>Client: Return Alarms object
    deactivate AlarmManager

    Client->>AlarmManager: deploy_alarms(alarms)
    activate AlarmManager
    AlarmManager->>ThreadPool: Create thread pool
    loop For each alarm
        ThreadPool->>AlarmManager: _deploy_single_alarm()
        AlarmManager->>AWS CloudWatch: put_metric_alarm()
    end
    AlarmManager-->>Client: Deployment complete
    deactivate AlarmManager

    Client->>AlarmManager: delete_alarms()
    AlarmManager->>AWS CloudWatch: delete_alarms()

    Client->>AlarmManager: scan_alarms()
    AlarmManager->>AWS CloudWatch: List existing alarms
```

### Alarm Manager

The Alarm Manager handles the creation and deployment of CloudWatch alarms across AWS accounts. Here's the components:

## Component Diagram

```mermaid
graph TB
    subgraph Monitoring Package
        AM[AlarmManager]
        ACM[AlarmConfigManager]
        AC[AlarmConfig]
        MC[MetricConfig]
        CWM[CWAgentMetrics]
        CONST[Constants]

        %% Main class relationships
        AM -->|uses| ACM
        AM -->|creates| AC
        AM -->|manages| CWM

        %% Config relationships
        AC -->|contains| MC
        ACM -->|loads| AC

        %% Dependencies
        AM -->|uses| CONST
        CWM -->|contains| MC

        %% Configuration files
        CF1[alarm_config.yaml]
        CF2[category_config.yaml]
        CF3[custom_config.yaml]

        ACM -->|loads| CF1
        ACM -->|loads| CF2
        ACM -->|loads| CF3

        %% External Services
        AWS[AWS CloudWatch]
        AM -->|interacts| AWS
    end

    %% Class details
    classDef main fill:#f9f,stroke:#333,stroke-width:2px
    classDef config fill:#bbf,stroke:#333,stroke-width:1px
    classDef external fill:#bfb,stroke:#333,stroke-width:1px
    classDef files fill:#ddd,stroke:#333,stroke-width:1px

    class AM main
    class ACM,AC,MC,CWM config
    class AWS external
    class CF1,CF2,CF3 files
    class CONST files
```

### Core Package

```mermaid
classDiagram
    class LandingZone {
        +String name
        +String env
        +String account_id
        +String app_id
        +String category
    }

    class LandingZoneManager {
        -List~LandingZone~ _lz_configs
        +__init__(lz_file)
        -_load_lz_configs(lz_file)
        +get_all_landing_zones()
        +get_landing_zone(lz_name)
    }

    class AWSSession {
        +Session session
        +String aws_access_key
        +String aws_secret_key
        +String security_token
        +String expire_date
        +String default_region
        +is_valid()
        +expires_in_seconds()
    }

    class SessionManager {
        -Dict~String,AWSSession~ _sessions
        +get_or_create_session(lz, role, region, role_session_name)
        +cleanup_session(session)
    }

    class Resource {
        +String type
        +String name
        +String id
    }

    class ResourceScanner {
        +Dict RESOURCE_CONFIG
        -List~Resource~ _managed_resources
        +__init__(session, region_name)
        +get_managed_resources(env)
        +get_resources_by_tag(tags, resource_config)
        -_fetch_resources_from_aws(tags, resource_type)
    }

    LandingZoneManager "1" *-- "*" LandingZone
    SessionManager "1" *-- "*" AWSSession
    ResourceScanner "1" *-- "*" Resource
    ResourceScanner --> AWSSession
    SessionManager --> LandingZone
```

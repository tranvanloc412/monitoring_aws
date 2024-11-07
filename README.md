# Project Name

Brief description of what this project does.

## Setup

### Prerequisites
- Python 3.x
- Docker (for nonprod environment)
- AWS credentials

### Installation
    python3 -m venv .venv
    source .venv/bin/activate
    pip3 install -r requirements.txt

# Assume jump repo
nonprod:
    docker run -it --rm -v ~/.aws:/home/samlf5/.aws cd.artifactory.ext.national.com.au/samlf5:0.7.0 -v --username {username} -a cmsnonprod -n 643141967929 
prod:
    Cyberark

## Authentication

### Production Environment
Authentication is managed through Cyberark.


## Key Improvements
- **Consolidated Configuration**: All landing zone YAML files merged into a single file for easier management
- **Improved Performance**: Replaced Ansible playbooks with direct Python implementation
  - Reduced network calls
  - Faster alarm deployment
  - Enhanced processing efficiency
- **Greater Flexibility**: Support for custom alarm configurations

## Future Improvements

### Deployment Safety
- Implement dry-run capability to validate changes before deployment
- Add pre-deployment verification for IAM roles and Landing Zone configurations (prod/nonprod)
- Develop comprehensive test suite for reliability

### Monitoring & Logging
- Implement detailed logging system
  - Store logs in CloudWatch and S3 for audit trails
  - Track all deployment activities and changes

### Automation
- Establish CI/CD pipeline for automated testing and deployment
- Create scheduled jobs for periodic execution
- Implement automatic updates for Landing Zone YAML configurations

### Infrastructure
- Enhance infrastructure validation
- Add automated scanning of resources


## Architecture

graph TD
    A[Main Script] --> B[Landing Zone Manager]
    B --> C[AWS Session Manager]
    C --> D[Resource Scanner]
    D --> E[Alarm Manager]
    E --> F[CloudWatch Alarm Definitions]
    F --> G[Alarm Deployment]



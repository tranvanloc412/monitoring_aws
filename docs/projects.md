# Project Overview

## Objective

* Automate the creation of AWS CloudWatch alerts for resources tagged with `managed_by = CMS` across approximately 100 CMS managed landing zones
* Resources include: EC2 (Windows and Linux), RDS, Load Balancers: ALB, NLB, FSx and EFS which are described in [CMS AWS Monioring](https://confluence.cms.gov/display/IT/CMS+AWS+Managed+Landing+Zone+Architecture)
* Goal: Reduce manual effort and minimize the risk of missing alerts due to infrequent reviews of Terraform configurations

## Scope

### Included

* CloudWatch alerts for resources based on categories (CAT_A, CAT_B, CAT_C, CAT_D)
* CAT_A: Most critical applications with strict thresholds, notifying the High SNS topic
* CAT_B: Less critical applications with higher thresholds, triggering the Medium SNS topic
* CAT_C: Applications with lower thresholds, notifying the Low SNS topic
* CAT_D: Applications that are not monitored

### Excluded

* Any resources not tagged with `managed_by = CMS`
* Management of resources outside CMS AWS managed landing zones

## Stakeholder Analysis

### Identify Stakeholders

* Primary Stakeholder: CMS AWS Team responsible for managing customer resources
* Secondary Stakeholders: Engineers who will use the tool on their laptops or CMS jump boxes

## Roles and Responsibilities

* CMS AWS Team
  * Use a jump role in the cmshub nonprod/prod landing zones to assume the spoke role in managed landing zones for managing alarms (create, delete, scan)
  * Store audit logs for all operations performed by the tool
  * Run the tool on team jump boxes or engineers’ laptops
  * Develop and maintain the tool using Python 3.10 or higher

## Current Process Assessment

### Process Mapping

* Existing Method: Using Terraform to create alarms for new landing zones
* Challenges with Current Method:
  * Repetitive and time-consuming manual configurations
  * Inability to predict monitored metrics in advance (e.g., disk usage on Linux, data drives on Windows)
  * Risk of missing alerts if engineers do not frequently review and update Terraform scripts

### Pain Points

* Efficiency Issues: Manual process leads to delays and potential errors
* Scalability Concerns: Managing alerts across 100 AWS landing zones is not sustainable with current methods
* Visibility Gaps: Lack of proactive monitoring leads to missed critical alerts

## Functional Requirements

### 1. Resource Categorization and Tagging

#### Category Assignment

* Resources are assigned to CAT_A, CAT_B, CAT_C or CAT_D based on the application or landing zone (LZ) they belong to
* Each landing zone hosts a specific application, and the category is defined per application/LZ

Example:

```yaml
landing_zone: cms
app_id: SPL-529
cost_centre: V_CMS_AWS
category: CAT_A
```

## CLI Commands

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

## User Feedback

* No interactive prompts needed at this time
* Output should include execution summaries and options for detailed logs
* Change Request Number
  * When running on production landing zones, the tool may prompt for a change request number in the future (not required now)

## Error Handling and Notifications

* Failure Scenarios
  * On errors like network timeouts or permission issues, the tool should skip or fail gracefully
  * Users can rerun the tool as needed
* Notifications
  * No need for additional alerts or notifications upon encountering errors at this time

## Technical Requirements

### Programming Language

* Develop the tool using Python 3.10 or higher

### AWS Services and APIs

* Utilize AWS SDKs (Boto3) for Python to interact with AWS services
* Implement multi-account access via existing cross-account IAM roles

### Scalability

* Ensure the tool can handle the scale of 100+ AWS landing zones efficiently
* Design the tool to accommodate additional landing zones in the future

### Performance

* Optimize for quick execution to minimize runtime on engineer laptops or jump boxes

### Development Practices

* Maintain a clear flow of code with readable variable names and comments
* Group related functions into modules for better organization

## Non-Functional Requirements

### Security

* Secure handling of credentials and role assumptions
* Store audit logs securely in the designated S3 bucket

### Compliance

* No specific compliance standards (e.g., HIPAA, GDPR) are required at this time

### Usability

* User-friendly commands and clear documentation
* Provide help messages and usage instructions

## Constraints and Assumptions

* Execution Environment
  * The tool can run in tooling or private subnets or on engineer laptops without internet access but must have access to AWS APIs
* Distribution Method
  * The tool will be distributed via a source code repository (GitHub)
* Python Libraries
  * No limitations on using external Python libraries beyond the approved list

## Future Scalability and Extensibility

* Scaling Considerations
  * Design the tool to handle more than 200 AWS landing zones in the future
* Extensibility
  * Plan for extending capabilities to manage additional resource types or services down the line

## Handling Unmanaged Resources

* Unmanaged Resources
  * The tool will ignore resources not tagged with managed_by = CMS
* Onboarding Process
  * The resource must be tagged with managed_by = CMS when onboarded to a CMS managed landing zone

## Handling Resource Deletion

* Alarm Cleanup
  * The tool should handle the deletion of CloudWatch alarms when resources are terminated or no longer meet the criteria
* Periodic Scans
  * No need for periodic scans to remove obsolete alarms at this time

## Next Steps

1. Finalize Requirements Document
   * Review and confirm all requirements with CMS AWS Team
   * Make any necessary adjustments based on feedback
2. Design Phase
   * Outline the tool’s architecture
   * Define modules, functions, and how to handle future expansions
3. Development
   * Begin coding according to the finalized requirements
   * Implement the CLI interface with specified commands
4. Testing
   * While formal testing is deferred, consider basic tests to ensure functionality
5. Deployment
   * Clean up the GitHub repository for current monitoring tool
   * Provide initial documentation for installation and usage

## Conclusion

By automating the creation and management of CloudWatch alerts, we will:

* Improve efficiency by reducing manual configurations
* Enhance monitoring coverage across all managed resources
* Minimize risks associated with missed alerts and unmonitored resources
* Lay the groundwork for future scalability and extensibility

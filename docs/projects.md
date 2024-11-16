# Project Overview

## Objective

* Automate the creation of AWS CloudWatch alerts for resources tagged with `managed_by = CMS` across approximately 200 AWS accounts.
* Resources include: EC2 (Windows and Linux), RDS, Load Balancers, FSx, EFS, etc.
* Goal: Reduce manual effort and minimize the risk of missing alerts due to infrequent reviews of Terraform configurations.

## Scope

### Included

* CloudWatch alerts for resources based on categories (e.g., CAT_A, CAT_B).
* CAT_A: Most critical applications with strict thresholds, notifying the High SNS topic.
* CAT_B: Less critical applications with higher thresholds, triggering the Medium SNS topic.

### Excluded

* Any resources not tagged with `managed_by = CMS`.
* Management of resources outside the specified AWS accounts.

## Stakeholder Analysis

### Identify Stakeholders

* Primary Stakeholder: CMS AWS Team responsible for managing customer resources.
* Secondary Stakeholders: Engineers who will use the tool on their laptops or CMS jump boxes.

### Roles and Responsibilities

* CMS AWS Team:
  * Use a jump role in the hub account to assume roles for managing landing zones and alert management (create, delete, scan).
  * Store audit logs for all operations performed by the tool.
  * Run the tool on team jump boxes or engineers' laptops.
  * Develop and maintain the tool using Python 3.10 or higher

## Current Process Assessment

### Process Mapping

* Existing Method: Using Terraform to create alarms for new landing zones.
* Challenges with Current Method:
  * Repetitive and time-consuming manual configurations.
  * Inability to predict monitored metrics in advance (e.g., disk usage on Linux, data drives on Windows).
  * Risk of missing alerts if engineers do not frequently review and update Terraform scripts.

### Pain Points

* Efficiency Issues: Manual process leads to delays and potential errors.
* Scalability Concerns: Managing alerts across 200 AWS accounts is not sustainable with current methods.
* Visibility Gaps: Lack of proactive monitoring leads to missed critical alerts.

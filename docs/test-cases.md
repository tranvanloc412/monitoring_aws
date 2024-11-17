# AWS Resource Management Tool Test Cases

This document outlines the functional test cases for the AWS Resource Management Tool.

## Functional Test Case: Create Alarms for One Landing Zone

- **Test Case ID**: FT-CA-001
- **Objective**: Verify that the system can create alarms for a single landing zone (LZ).
- **Preconditions**:
  - Access to the system with necessary permissions.
  - The landing zone is properly configured and accessible.
- **Test Data**:
  - Landing Zone ID: `LZ-12345`

## Steps

1. **Initialize AlarmManager**:
   - Call the `Initialize()` method with parameters:
     - `landing_zone`: `LZ-12345`
     - `aws_session`: Valid AWS session object
     - Additional parameters as required.
2. **Load Configurations**:
   - Ensure that `load_configs()` retrieves the correct configurations.
3. **Scan Existing Alarms**:
   - Confirm that existing alarms are fetched from AWS CloudWatch.
4. **Create Alarm Definitions**:
   - Invoke `create_all_alarm_definitions()`.
   - Verify that alarm definitions are created for all resources in the landing zone.
5. **Deploy Alarms**:
   - Call `deploy_alarms(alarms)`.
   - Ensure alarms are successfully deployed to AWS CloudWatch.

## Expected Results

- **AlarmManager Initialization**: Should complete without errors.
- **Configurations Loaded**: Correct configurations are loaded from `ConfigManager`.
- **Existing Alarms Scanned**: Existing alarms are retrieved and processed.
- **Alarm Definitions Created**: Alarm definitions are correctly created for each resource.
- **Alarms Deployed**: Alarms are deployed to AWS CloudWatch, and confirmation is received.

## Postconditions

- Alarms are active and monitoring the specified resources in the landing zone.
- No unintended side effects or errors occur during the process.

## Notes

- **Error Handling**: Ensure that the system gracefully handles any exceptions.
- **Logging**: Verify that appropriate logs are generated at each step.

---

*Prepared by*: Van Loc Tran  
*Date*: 2024-11-17

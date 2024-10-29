from resources_manager import ResourceScanner

# Initialize the scanner
scanner = ResourceScanner(region_name="ap-southeast-1")

# Get resources managed by 'CM'
managed_resources = scanner.get_managed_resources()

# Print each resource's details
for resource in managed_resources:
    print(resource.to_dict())
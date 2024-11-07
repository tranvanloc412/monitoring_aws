## boto 3 to get all cloudwatch metrics in a namespace with pagination 10 items at a time
import boto3


def get_all_metrics(namespace: str):
    client = boto3.client("cloudwatch")
    paginator = client.get_paginator("list_metrics")

    page_iterator = paginator.paginate(Namespace=namespace)

    # Iterate through each page
    for page_number, page in enumerate(page_iterator, start=1):
        metrics = page["Metrics"]
        print(f"Page {page_number}: Got {len(metrics)} metrics")
        for metric in metrics:
            print(metric)


# Example usage
if __name__ == "__main__":

    get_all_metrics("AWS/EC2")

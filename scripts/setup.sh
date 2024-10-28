aws sts assume-role \
    --role-arn arn:aws:iam::891377130283:role/HIPCMSProvisionSpokeRole \
    --role-session-name cw-monitoring

lz_no="891377130283"
session_name="monitoring"
aws sts assume-role --role-arn "arn:aws:iam::${lz_no}:role/HIPCMSProvisionSpokeRole" --role-session-name $session_name | jq -r '.Credentials | "export AWS_ACCESS_KEY_ID=\(.AccessKeyId)\nexport AWS_SECRET_ACCESS_KEY=\(.SecretAccessKey)\nexport AWS_SECURITY_TOKEN=\(.SessionToken)\nexport AWS_SESSION_TOKEN=\(.SessionToken)"'
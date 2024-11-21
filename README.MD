### this repo containes a lambda function that triggers a job in eks. the job uses a secret.

## Requirements

### Lambda Role

To set up the required permissions, ensure the following steps are completed:

1. **OIDC Provider for EKS**:
   - Create an **OIDC provider** for your EKS cluster.
   - This allows linking the Kubernetes service account to the Lambda role.

2. **Add Lambda Role to IAM Access Entries in EKS**:
   - Update the `aws-auth` ConfigMap in the `kube-system` namespace to include the Lambda role.

---

### Lambda Role Permissions

The Lambda role must have the following permissions:

#### 1. Managed Policies
- `AmazonEKSClusterPolicy`
- `AWSLambdaVPCAccessExecutionRole`

#### 2. For Job Secret
Attach the following managed policy:
- `SecretsManagerReadWrite` to allow access to secrets stored in AWS Secrets Manager.

#### 3. Inline Policy
Attach the following inline policy to the Lambda role for access to required resources:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt",
                "kms:DescribeKey"
            ],
            "Resource": "arn:aws:kms:<region>:<account>:key/<key>"
        },
        {
            "Effect": "Allow",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::secrets-bucket"
        }
    ]
}

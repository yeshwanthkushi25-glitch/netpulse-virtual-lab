---
name: aws-learner-lab-deploy
description: >-
  Automated zero-friction serverless deployment and static hosting playbook for AWS Academy
  Learner Lab sandbox environments. Use when designing, packaging, or deploying CloudFormation,
  Lambda, DynamoDB, API Gateway, or S3 applications in educational or restricted AWS accounts.
---

# AWS Academy Learner Lab Serverless Deployment Playbook

This skill provides comprehensive instructions for deploying serverless architectures (CloudFormation, AWS Lambda, Amazon DynamoDB, Amazon API Gateway, and Amazon S3) into **AWS Academy Learner Lab (Vocareum)** environments without violating Service Control Policies (SCPs) or hitting common deployment pitfalls.

---

## 1. Learner Lab Environment & Policy Constraints

AWS Academy Learner Lab operates within strict sandbox constraints:
- **No IAM Role Creation**: `iam:CreateRole`, `iam:CreatePolicy`, and `iam:AttachRolePolicy` actions are blocked. All services must assume the pre-existing role:
  ```
  arn:aws:iam::<AccountId>:role/LabRole
  ```
- **Temporary Session Tokens**: Credentials expire every 4 hours. You must always handle all 3 keys:
  - `AWS_ACCESS_KEY_ID` (starts with `ASIA...`)
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_SESSION_TOKEN`
- **Region**: Defaults to `us-east-1` in standard course environments.
- **Console vs. CLI Guidance**:
  - In Vocareum, `[ AWS Details ]` has two tabs:
    1. **SSH Key**: Downloads `labsuser.pem` (for EC2 SSH access only).
    2. **AWS CLI**: Contains the API access keys. Direct users to click `[ Show ]` under AWS CLI.

---

## 2. CloudFormation Template Best Practices for Learner Lab

### A. Role Assignment
Always parameterize role assignment so templates work both inside and outside Learner Lab:

```yaml
Parameters:
  UseLabRole:
    Type: String
    Default: 'true'
    AllowedValues: ['true', 'false']
    Description: Set to 'true' for AWS Academy Learner Lab.

Conditions:
  IsInLearnerLab: !Equals [!Ref UseLabRole, 'true']
  CreateCustomRole: !Equals [!Ref UseLabRole, 'false']

Resources:
  MyLambdaFunction:
    Type: AWS::Lambda::Function
    Properties:
      Runtime: python3.12
      Handler: index.handler
      Role: !If
        - IsInLearnerLab
        - !Sub 'arn:aws:iam::${AWS::AccountId}:role/LabRole'
        - !GetAtt CustomLambdaRole.Arn
```

### B. Condition Invariants
> [!CRITICAL]
> In AWS CloudFormation, a resource's `Condition:` attribute MUST be a string reference to a named condition under the top-level `Conditions:` block.
> **DO NOT** use inline intrinsic functions like `Condition: !Equals [...]` directly on a resource, which causes:
> `Template format error: Every Condition member must be a string.`

---

## 3. Public S3 Static Website Hosting

Learner Lab allows S3 static websites if configured with public access unblocked:

```yaml
  DashboardBucket:
    Type: AWS::S3::Bucket
    Properties:
      WebsiteConfiguration:
        IndexDocument: index.html
        ErrorDocument: index.html
      PublicAccessBlockConfiguration:
        BlockPublicAcls: false
        BlockPublicPolicy: false
        IgnorePublicAcls: false
        RestrictPublicBuckets: false

  DashboardBucketPolicy:
    Type: AWS::S3::BucketPolicy
    Properties:
      Bucket: !Ref DashboardBucket
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Sid: PublicReadGetObject
            Effect: Allow
            Principal: '*'
            Action: s3:GetObject
            Resource: !Sub '${DashboardBucket.Arn}/*'
```

---

## 4. Automated Python Deployer Pattern (`boto3`)

Implement a single-file deployer script (e.g. `scripts/deploy_aws.py`) using `boto3`:

1. **Session Setup**:
   ```python
   session = boto3.Session(
       aws_access_key_id=access_key,
       aws_secret_access_key=secret_key,
       aws_session_token=session_token,
       region_name='us-east-1'
   )
   ```
2. **Identity Verification**:
   ```python
   identity = session.client('sts').get_caller_identity()
   account_id = identity['Account']
   ```
3. **CloudFormation Deploy & Wait**:
   ```python
   cf = session.client('cloudformation')
   cf.create_stack(
       StackName=stack_name,
       TemplateBody=template_body,
       Parameters=[{'ParameterKey': 'UseLabRole', 'ParameterValue': 'true'}],
       Capabilities=['CAPABILITY_NAMED_IAM', 'CAPABILITY_AUTO_EXPAND']
   )
   waiter = cf.get_waiter('stack_create_complete')
   waiter.wait(StackName=stack_name)
   ```
4. **S3 Asset Synchronization**:
   - Extract `DashboardWebsiteUrl` and `StatusApiUrl` from stack outputs.
   - Inject `StatusApiUrl` into frontend configuration (`config.js`).
   - Upload frontend files with appropriate MIME types and cache headers.
5. **Auto-Launch**:
   ```python
   import webbrowser
   webbrowser.open(website_url)
   ```

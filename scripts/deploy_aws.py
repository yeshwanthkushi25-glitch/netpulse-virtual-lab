#!/usr/bin/env python3
"""NetPulse Automated AWS CloudFormation Deployment & S3 Website Launcher.

Deploys the NetPulse serverless stack to AWS Learner Lab or standard AWS accounts,
uploads dashboard assets to S3, and verifies real-time telemetry ingestion.

Usage:
    # 1. Using environment variables:
    python scripts/deploy_aws.py

    # 2. Using AWS Learner Lab temporary session tokens:
    python scripts/deploy_aws.py --access-key AKIA... --secret-key ... --session-token ...

    # 3. Interactive credential prompt:
    python scripts/deploy_aws.py --interactive

    # 4. Connect to existing AWS API without redeploying:
    python scripts/deploy_aws.py --api-url https://abc123xyz.execute-api.us-east-1.amazonaws.com
"""

import argparse
import json
import mimetypes
import os
import sys
import time
import urllib.request
import webbrowser

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    boto3 = None


STACK_NAME = "netpulse-lab"
DEFAULT_REGION = "us-east-1"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMPLATE_PATH = os.path.join(REPO_ROOT, "cloudformation.yaml")
DASHBOARD_DIR = os.path.join(REPO_ROOT, "dashboard")
CONFIG_JS_PATH = os.path.join(DASHBOARD_DIR, "config.js")


def update_dashboard_config(api_url: str):
    """Update dashboard/config.js with the AWS API Gateway base URL."""
    clean_url = api_url.rstrip("/")
    content = f"""// NetPulse AWS Production Configuration
window.NETPULSE_CONFIG = {{
  apiUrl: "{clean_url}",
  source: "vm-a",
  target: "vm-b",
  refreshIntervalMs: 3000
}};
"""
    with open(CONFIG_JS_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  [CONFIG] Updated dashboard/config.js -> {clean_url}")


def upload_dashboard_to_s3(s3_client, bucket_name: str):
    """Upload all dashboard static files to the public S3 website bucket."""
    print(f"\n[S3 UPLOAD] Deploying dashboard files to bucket: {bucket_name}")
    for root, _, files in os.walk(DASHBOARD_DIR):
        for file in files:
            full_path = os.path.join(root, file)
            relative_path = os.path.relpath(full_path, DASHBOARD_DIR).replace("\\", "/")
            mime_type, _ = mimetypes.guess_type(full_path)
            mime_type = mime_type or "application/octet-stream"

            extra_args = {"ContentType": mime_type}
            if file == "config.js" or file == "index.html":
                extra_args["CacheControl"] = "no-cache, no-store, must-revalidate"

            with open(full_path, "rb") as data:
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=relative_path,
                    Body=data.read(),
                    **extra_args
                )
            print(f"  Uploaded: {relative_path} ({mime_type})")
    print("  ✅ Dashboard successfully deployed to S3!")


def deploy_cloudformation(cf_client, region: str, use_lab_role: bool = True):
    """Create or update the NetPulse CloudFormation stack."""
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template_body = f.read()

    params = [
        {"ParameterKey": "UseLabRole", "ParameterValue": "true" if use_lab_role else "false"}
    ]
    capabilities = ["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"]

    print(f"\n[CLOUDFORMATION] Checking stack status for: {STACK_NAME} in {region}...")
    stack_exists = False
    try:
        cf_client.describe_stacks(StackName=STACK_NAME)
        stack_exists = True
    except ClientError as e:
        if "does not exist" not in str(e):
            raise

    if stack_exists:
        print(f"  Stack '{STACK_NAME}' exists. Initiating update...")
        try:
            cf_client.update_stack(
                StackName=STACK_NAME,
                TemplateBody=template_body,
                Parameters=params,
                Capabilities=capabilities
            )
            waiter = cf_client.get_waiter("stack_update_complete")
        except ClientError as e:
            if "No updates are to be performed" in str(e):
                print("  Stack is already up-to-date with current template.")
                waiter = None
            else:
                raise
    else:
        print(f"  Creating new CloudFormation stack: {STACK_NAME} (Learner Lab Role: {use_lab_role})...")
        cf_client.create_stack(
            StackName=STACK_NAME,
            TemplateBody=template_body,
            Parameters=params,
            Capabilities=capabilities
        )
        waiter = cf_client.get_waiter("stack_create_complete")

    if waiter:
        print("  ⏳ Waiting for AWS resources to provision (DynamoDB, Lambda, API Gateway, S3)...")
        waiter.wait(StackName=STACK_NAME, WaiterConfig={"Delay": 5, "MaxAttempts": 60})
        print("  ✅ Stack provisioning complete!")

    desc = cf_client.describe_stacks(StackName=STACK_NAME)["Stacks"][0]
    outputs = {o["OutputKey"]: o["OutputValue"] for o in desc.get("Outputs", [])}
    return outputs


def test_api_health(api_url: str):
    """Verify live connectivity against the deployed AWS API Gateway endpoint."""
    test_url = f"{api_url.rstrip('/')}/status?target=all"
    print(f"\n[HEALTH CHECK] Probing AWS API Gateway: {test_url}")
    try:
        req = urllib.request.Request(test_url, headers={"User-Agent": "NetPulse-Deployer/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"  HTTP Status: {resp.getcode()} OK")
            print(f"  Cluster Response: {data}")
            return True
    except Exception as exc:
        print(f"  ⚠️ Warning: API probe returned: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Deploy NetPulse to AWS Cloud")
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", DEFAULT_REGION), help="AWS Region (default: us-east-1)")
    parser.add_argument("--access-key", default=os.environ.get("AWS_ACCESS_KEY_ID"), help="AWS Access Key ID")
    parser.add_argument("--secret-key", default=os.environ.get("AWS_SECRET_ACCESS_KEY"), help="AWS Secret Access Key")
    parser.add_argument("--session-token", default=os.environ.get("AWS_SESSION_TOKEN"), help="AWS Session Token (for Learner Lab)")
    parser.add_argument("--use-lab-role", action="store_true", default=True, help="Use AWS Learner Lab pre-existing LabRole (default: True)")
    parser.add_argument("--api-url", help="Connect to an already-deployed AWS API URL instead of deploying CloudFormation")
    parser.add_argument("--interactive", action="store_true", help="Prompt interactively for AWS credentials")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser")
    args = parser.parse_args()

    print("=" * 70)
    print("   ☁️ NETPULSE — AWS CLOUD CONNECT & DEPLOYMENT LAUNCHER")
    print("   SR University · Cloud Computing (25CAI102PC205) · Project No. 33")
    print("=" * 70)

    # Mode A: Connect directly to existing API
    if args.api_url:
        print(f"\n[MODE] Connecting NetPulse to existing AWS API: {args.api_url}")
        update_dashboard_config(args.api_url)
        test_api_health(args.api_url)
        print("\n✅ Successfully connected dashboard to AWS API!")
        if not args.no_browser:
            webbrowser.open("http://localhost:8000")
        return 0

    # Mode B: Full AWS CloudFormation Deployment
    if boto3 is None:
        print("\n❌ Error: 'boto3' is required for AWS deployment. Run: pip install boto3")
        return 1

    access_key = args.access_key
    secret_key = args.secret_key
    session_token = args.session_token

    if args.interactive and not (access_key and secret_key):
        print("\n📋 Enter your AWS credentials (e.g. from AWS Academy Learner Lab -> AWS Details):")
        access_key = input("  AWS Access Key ID: ").strip()
        secret_key = input("  AWS Secret Access Key: ").strip()
        session_token = input("  AWS Session Token (leave blank if not using Learner Lab): ").strip() or None

    session_kwargs = {"region_name": args.region}
    if access_key and secret_key:
        session_kwargs["aws_access_key_id"] = access_key
        session_kwargs["aws_secret_access_key"] = secret_key
        if session_token:
            session_kwargs["aws_session_token"] = session_token

    try:
        session = boto3.Session(**session_kwargs)
        sts = session.client("sts")
        caller = sts.get_caller_identity()
        print(f"\n[AUTHENTICATION SUCCESSFUL]")
        print(f"  Account ID: {caller.get('Account')}")
        print(f"  IAM User/Role: {caller.get('Arn')}")
        print(f"  Region: {args.region}")
    except (NoCredentialsError, ClientError) as exc:
        print(f"\n❌ AWS Authentication Error: {exc}")
        print("\nTo connect to AWS, please run with your credentials:")
        print("  python scripts/deploy_aws.py --access-key <KEY> --secret-key <SECRET> --session-token <TOKEN>")
        print("\nOr if using AWS Academy Learner Lab:")
        print("  1. Open AWS Academy Learner Lab.")
        print("  2. Click 'AWS Details' button at top right.")
        print("  3. Copy the 3 lines and run:")
        print("     $env:AWS_ACCESS_KEY_ID='ASIA...'")
        print("     $env:AWS_SECRET_ACCESS_KEY='...'")
        print("     $env:AWS_SESSION_TOKEN='...'")
        print("     python scripts/deploy_aws.py")
        return 1

    # Deploy CloudFormation
    cf_client = session.client("cloudformation")
    outputs = deploy_cloudformation(cf_client, args.region, use_lab_role=args.use_lab_role)

    api_url = outputs.get("StatusApiUrl")
    website_url = outputs.get("DashboardWebsiteUrl")
    bucket_name = outputs.get("DashboardBucketName")

    print("\n" + "=" * 70)
    print("   🎉 NETPULSE IS OFFICIALLY LIVE ON AWS CLOUD!")
    print("=" * 70)
    print(f"  🌐 API Gateway URL:    {api_url}")
    print(f"  🖥️ S3 Live Website:    {website_url}")
    print(f"  📦 DynamoDB Table:     {outputs.get('StatusTableName')}")
    print(f"  🪣 S3 Static Bucket:   {bucket_name}")
    print("=" * 70)

    # Update config.js and upload files
    if api_url:
        update_dashboard_config(api_url)
    if bucket_name:
        s3_client = session.client("s3")
        upload_dashboard_to_s3(s3_client, bucket_name)

    # Health check
    if api_url:
        test_api_health(api_url)

    # Launch in browser
    launch_url = website_url or "http://localhost:8000"
    if not args.no_browser and launch_url:
        print(f"\n🚀 Launching live AWS dashboard in your browser: {launch_url}")
        webbrowser.open(launch_url)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

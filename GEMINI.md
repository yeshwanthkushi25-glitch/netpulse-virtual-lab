# Antigravity Persistent Rule: GitHub Demo Pictures & Screenshots

Whenever working on or uploading any project to GitHub:
1. **Always Upload Demo Pictures**: Generate and upload high-fidelity visual assets, UI screenshots (operational, degraded, failure states), terminal logs, and architecture diagrams directly to GitHub.
2. **Prominent Root Folder**: Place all screenshots in a top-level `screenshots/` directory in the repository root as well as in `docs/screenshots/`.
3. **Embed in README**: Embed all screenshots directly into `README.md` and academic submission reports so they render on the GitHub repository front page.
4. **Remind the User**: Always explicitly confirm and remind the user that the demo pictures and visual assets are live on GitHub for every project.

---

# AWS Academy Learner Lab Deployment Invariants

Whenever building or deploying applications to an AWS Academy Learner Lab environment:
1. **Pre-existing LabRole Only**: Never attempt to create custom IAM roles with `iam:CreateRole`. Always attach `arn:aws:iam::<AccountId>:role/LabRole` to Lambda functions, EC2 instances, and services.
2. **Session Token Handling**: Always account for `AWS_SESSION_TOKEN` in SDK sessions alongside `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.
3. **CloudFormation Conditions**: Never use inline `!Equals` on a resource's `Condition:` key; declare conditions under `Conditions:` and reference them by string name.
4. **Credential Guidance**: If guiding the user to retrieve lab credentials, explicitly direct them to click `[ Show ]` under the `AWS CLI` section of the Vocareum `[ AWS Details ]` modal, distinguishing it from the SSH `.pem` key.

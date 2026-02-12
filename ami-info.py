import os
import boto3
import cfnresponse

def lambda_handler(event, context):
    """
    Generic CloudFormation Custom Resource:
    Finds AMIs by name patterns and returns their IDs as:
      - idWEB
      - idAPP
      - idBAST

    Configure via environment variables:
      AWS_REGION (optional)
      AMI_WEB_PATTERN (default: "*APP-QA-WEB*")
      AMI_APP_PATTERN (default: "*APP-QA-APP*")
      AMI_BASTION_PATTERN (default: "*APP-QA-BASTION*")
    """

    region = os.environ.get("AWS_REGION", "us-east-1")

    web_pattern = os.environ.get("AMI_WEB_PATTERN", "*APP-QA-WEB*")
    app_pattern = os.environ.get("AMI_APP_PATTERN", "*APP-QA-APP*")
    bastion_pattern = os.environ.get("AMI_BASTION_PATTERN", "*APP-QA-BASTION*")

    ec2 = boto3.resource("ec2", region)

    # We filter all images matching any of the patterns.
    # (Optionally you could also filter by "state=available" and "is-public=false".)
    images = ec2.images.filter(
        Filters=[
            {"Name": "name", "Values": [web_pattern, app_pattern, bastion_pattern]},
        ]
    )

    ami_ids = {"idWEB": None, "idAPP": None, "idBAST": None}

    try:
        for image in images:
            name = (image.name or "").upper()

            # Match by pattern intent (simple contains heuristics).
            # If you want strict pattern matching, use fnmatch on the original name.
            if "WEB" in name and ami_ids["idWEB"] is None:
                ami_ids["idWEB"] = image.id

            if "APP" in name and ami_ids["idAPP"] is None:
                ami_ids["idAPP"] = image.id

            if "BASTION" in name and ami_ids["idBAST"] is None:
                ami_ids["idBAST"] = image.id

        # Validate findings (for Create/Update; on Delete we can still respond SUCCESS)
        missing = [k for k, v in ami_ids.items() if v is None]
        if missing and event.get("RequestType") in ("Create", "Update"):
            raise RuntimeError(
                f"Missing AMIs for keys: {missing}. "
                f"Check patterns: WEB={web_pattern}, APP={app_pattern}, BASTION={bastion_pattern} "
                f"and region: {region}"
            )

        # Always respond to CloudFormation
        cfnresponse.send(
            event,
            context,
            cfnresponse.SUCCESS,
            ami_ids,
            physicalResourceId="AMIInfoCustomResource"
        )

    except Exception as e:
        # If something goes wrong, return FAILED so the stack shows the error
        cfnresponse.send(
            event,
            context,
            cfnresponse.FAILED,
            {"Error": str(e), **ami_ids},
            physicalResourceId="AMIInfoCustomResource"
        )

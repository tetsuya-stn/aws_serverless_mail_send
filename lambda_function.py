import boto3
import dataclasses
import json
import os
import time


@dataclasses.dataclass(frozen=True)
class MailData:
    subject: str
    message: str
    to_address: str
    sender_address: str = dataclasses.field(init=False)

    def __post_init__(self):
        if not self.subject or not self.message or not self.to_address:
            raise ValueError("Parameters not correct.")
        object.__setattr__(self, "sender_address", os.environ["SENDER_MAIL"])


def get_ses_region(service_name: str):
    client = boto3.client("dynamodb")

    try:
        response = client.get_item(
            TableName="SesRegionManagement",
            Key={"ServiceName": {"S": service_name}},
        )
        print(response)
        ses_region = response["Item"]["RegionName"]["S"]
    except Exception as err:
        print(f"get_ses_region error: {err}")
        return os.environ["SES_DEFAULT_REGION"]
    else:
        return ses_region


def lock_table(lockMailKey: str):
    try:
        if not lockMailKey:
            return False

        client = boto3.client("dynamodb")
        expirationUnixTime = int(time.time()) + int(os.environ["TTL_SEC_FOR_TABLE"])

        response = client.put_item(
            TableName="MailQueueLockTable",
            Item={
                "LockMailKey": {"S": lockMailKey},
                "ExpirationUnixTime": {"N": str(expirationUnixTime)},
            },
            ConditionExpression="attribute_not_exists(LockMailKey)",
        )
        print(response)
        return True

    except Exception as err:
        print(err)
        return False


def send_mail(mail_data: MailData, region: str):
    client = boto3.client("ses", region_name=region)

    client.send_email(
        Destination={"ToAddresses": [mail_data.to_address]},
        Message={
            "Body": {
                "Text": {
                    "Charset": "UTF-8",
                    "Data": mail_data.message,
                }
            },
            "Subject": {
                "Charset": "UTF-8",
                "Data": mail_data.subject,
            },
        },
        Source=mail_data.sender_address,
    )


def lambda_handler(event, context):
    print(event)
    batch_item_failures = []
    if event:
        for record in event["Records"]:
            try:
                body = json.loads(record["body"])
                region = get_ses_region(body.get("service_name", None))

                try:
                    mail_data = MailData(
                        body.get("subject", None),
                        body.get("message", None),
                        body.get("address", None),
                    )
                except ValueError as err:
                    print(err)
                    continue

                if lock_table(record["messageId"]):
                    send_mail(
                        mail_data,
                        region,
                    )
                else:
                    print(f"{record['messageId']}: DynamoDB lock error.")
                    continue

            except Exception as err:
                print(err)
                batch_item_failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": batch_item_failures}

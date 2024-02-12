import boto3
import json
import os
import time
# from aws_lambda_powertools import Logger

# logger = Logger(child=True)

SENDER_MAIL = os.environ["SENDER_MAIL"]
TTL_SEC_FOR_TABLE = int(os.environ["TTL_SEC_FOR_TABLE"])


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
        print(err)
        # logger.error(err)
        return None
    else:
        return ses_region


def lock_table(lockMailKey: str):
    try:
        if not lockMailKey:
            pass  # エラーハンドリング

        client = boto3.client("dynamodb")
        expirationUnixTime = int(time.time()) + TTL_SEC_FOR_TABLE

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


def send_mail(source: str, to_address: str, subject: str, body: str, region: str):
    client = boto3.client("ses", region_name=region)

    response = client.send_email(
        Destination={"ToAddresses": [to_address]},
        Message={
            "Body": {
                "Text": {
                    "Charset": "UTF-8",
                    "Data": body,
                }
            },
            "Subject": {
                "Charset": "UTF-8",
                "Data": subject,
            },
        },
        Source=source,
    )

    return response


def lambda_handler(event, context):
    print(event)
    batch_item_failures = []
    if event:
        for record in event["Records"]:
            try:
                body = json.loads(record["body"])
                subject = body.get("subject", None)
                message = body.get("message", None)
                to_address = body.get("address", None)
                region = get_ses_region(body.get("service_name", None))

                if (
                    subject is None
                    or message is None
                    or to_address is None
                    or region is None
                ):
                    print(f"{record['messageId']}: Parameters not correct.")
                    continue

                if not lock_table(record["messageId"]):
                    print(f"{record['messageId']}: DynamoDB lock error.")
                    continue

                send_mail_response = send_mail(
                    SENDER_MAIL, to_address, subject, message, region
                )
                print(send_mail_response)
            except Exception as err:
                print(err)
                batch_item_failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": batch_item_failures}

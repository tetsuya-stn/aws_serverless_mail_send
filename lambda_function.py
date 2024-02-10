import boto3
import json
import os
import time
# from aws_lambda_powertools import Logger

# logger = Logger(child=True)

SENDER_MAIL = os.environ["SENDER_MAIL"]
TTL_SEC_FOR_TABLE = int(os.environ["TTL_SEC_FOR_TABLE"])


def get_record(record: dict):
    pass


def get_ses_region(service_name: str):
    client = boto3.client("dynamodb")

    try:
        response = client.get_item(
            TableName="SesRegionManagement",
            Key={"ServiceName": {"S": service_name}},
        )
        print(response)
    except Exception as err:
        print(err)
        # logger.error(err)
        return None
    else:
        return response["Item"]["RegionName"].get("S", None)


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
    sqs_batch_response = {}
    if event:
        for record in event["Records"]:
            try:
                body = json.loads(record["body"])
                subject = body.get("subject", None)
                message = body.get("message", None)
                to_address = body.get("address", None)
                region = get_ses_region("test_service")
                # region = "ap-northeast-1"

                if message is None:
                    # ログ出力
                    continue
                elif to_address is None:
                    # ログ出力
                    continue
                elif region is None:
                    # ログ出力
                    continue

                if not lock_table(record["messageId"]):
                    print("DynamoDB Lock Error.")
                    continue

                send_mail_response = send_mail(
                    SENDER_MAIL, to_address, subject, message, region
                )
                print(send_mail_response)
            except Exception as err:
                print(err)
                batch_item_failures.append({"itemIdentifier": record["messageId"]})

        sqs_batch_response["batchItemFailures"] = batch_item_failures
        print(sqs_batch_response)

    return sqs_batch_response

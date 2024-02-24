import boto3
import dataclasses
import logging
import json
import os
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclasses.dataclass(frozen=True)
class MailData:
    """メールのデータを表すクラス。
    Attributes:
        subject (str): メールの件名。
        message (str): メールの本文。
        to_address (str): 宛先メールアドレス。
        sender_address (str): 送信元メールアドレス。環境変数から取得。
    Raises:
        ValueError: 件名、本文、宛先メールアドレスのいずれかが空の場合に発生。
    Notes:
        このクラスは不変（immutable）です。すべての属性は読み取り専用です。
    """

    subject: str
    message: str
    to_address: str
    sender_address: str = dataclasses.field(init=False)

    def __post_init__(self):
        if not self.subject or not self.message or not self.to_address:
            raise ValueError("Parameters not correct.")
        object.__setattr__(self, "sender_address", os.environ["SENDER_MAIL"])


def get_ses_region(service_name: str) -> str:
    client = boto3.client("dynamodb")

    try:
        response = client.get_item(
            TableName="SesRegionManagement",
            Key={"ServiceName": {"S": service_name}},
        )
        ses_region = response["Item"]["RegionName"]["S"]
    except Exception as err:
        logger.warning(f"Failed to get SES region: {err}")
        return os.environ.get("SES_DEFAULT_REGION", "ap-northeast-1")
    else:
        return ses_region


def lock_table(lockMailKey: str) -> bool:
    try:
        if not lockMailKey:
            return False

        client = boto3.client("dynamodb")
        expirationUnixTime = int(time.time()) + int(os.environ["TTL_SEC_FOR_TABLE"])

        client.put_item(
            TableName="MailQueueLockTable",
            Item={
                "LockMailKey": {"S": lockMailKey},
                "ExpirationUnixTime": {"N": str(expirationUnixTime)},
            },
            ConditionExpression="attribute_not_exists(LockMailKey)",
        )
        return True

    except Exception as err:
        logger.error(f"Failed to lock table: {err}")
        return False


def send_mail(mail_data: MailData, region: str) -> None:
    client = boto3.client("ses", region_name=region)

    try:
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
    except Exception as err:
        logger.error(f"Failed to send email: {err}")


def lambda_handler(event, context):
    logger.info(f"Received event: {event}")
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
                    logger.error(f"Invalid mail data: {err}")
                    continue

                if lock_table(record["messageId"]):
                    send_mail(
                        mail_data,
                        region,
                    )
                else:
                    logger.error(f"DynamoDB lock error for {record['messageId']}")
                    continue

            except Exception as err:
                logger.error(f"An error occurred: {err}")
                batch_item_failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": batch_item_failures}

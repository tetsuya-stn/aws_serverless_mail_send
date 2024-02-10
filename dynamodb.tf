resource "aws_dynamodb_table" "mail_send_duplication" {
  name         = "MailQueueLockTable"
  hash_key     = "LockMailKey"
  billing_mode = "PAY_PER_REQUEST"

  deletion_protection_enabled = true

  ttl {
    attribute_name = "ExpirationUnixTime"
    enabled        = true
  }

  attribute {
    name = "LockMailKey"
    type = "S"
  }
}

resource "aws_dynamodb_table" "ses_region_management" {
  name         = "SesRegionManagement"
  hash_key     = "ServiceName"
  billing_mode = "PAY_PER_REQUEST"

  deletion_protection_enabled = true

  attribute {
    name = "ServiceName"
    type = "S"
  }
}

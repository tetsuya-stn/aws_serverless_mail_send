resource "aws_lambda_function" "mail_send" {
  architectures                  = ["arm64"]
  function_name                  = "MailSendFunction"
  runtime                        = "python3.12"
  handler                        = "lambda_function.lambda_handler"
  package_type                   = "Zip"
  filename                       = "./lambda_function.py.zip"
  reserved_concurrent_executions = 1
  publish                        = false
  role                           = aws_iam_role.lambda_send_mail.arn
  timeout                        = 30

  environment {
    variables = {
      SENDER_MAIL       = "" # 送信元メールアドレス
      TTL_SEC_FOR_TABLE = 345600
    }
  }
  ephemeral_storage {
    size = 512
  }
  tracing_config {
    mode = "PassThrough"
  }
  lifecycle {
    ignore_changes = [
      environment,
      filename,
      version,
      source_code_hash,
      source_code_size,
    ]
  }
}

resource "aws_lambda_event_source_mapping" "sqs_mail_send" {
  event_source_arn = aws_sqs_queue.mail_queue.arn
  function_name    = aws_lambda_function.mail_send.arn

  batch_size                         = 5
  maximum_batching_window_in_seconds = 10

  function_response_types = ["ReportBatchItemFailures"]
}

resource "aws_sqs_queue" "mail_queue" {
  name                       = "MailQueue"
  fifo_queue                 = false
  visibility_timeout_seconds = 30
  receive_wait_time_seconds  = 10
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.mail_dead_lettter_queue.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "mail_dead_lettter_queue" {
  name       = "MailDeadLetterQueue"
  fifo_queue = false
}

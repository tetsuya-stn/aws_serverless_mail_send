resource "aws_iam_role" "lambda_send_mail" {
  name = "ses-send-email-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_policy" "lambda_send_mail" {
  name = "ses-send-email-policy"
  policy = jsonencode({
    "Version" = "2012-10-17",
    "Statement" = [
      {
        "Effect" = "Allow",
        "Action" = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ],
        "Resource" = "*"
      },
      {
        "Effect" = "Allow",
        "Action" = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Scan",
          "dynamodb:UpdateItem"
        ],
        "Resource" = [
          aws_dynamodb_table.mail_send_duplication.arn,
          aws_dynamodb_table.ses_region_management.arn
        ]
      },
      {
        "Effect" = "Allow",
        "Action" = [
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ReceiveMessage"
        ],
        "Resource" = aws_sqs_queue.mail_queue.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_send_mail" {
  role       = aws_iam_role.lambda_send_mail.name
  policy_arn = aws_iam_policy.lambda_send_mail.arn
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_send_mail.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

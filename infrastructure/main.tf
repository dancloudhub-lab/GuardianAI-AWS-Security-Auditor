# 1. AWS Provider Configuration
provider "aws" {
  region = "us-east-1"
}

# 2. SNS Topic for Security Alerts
resource "aws_sns_topic" "security_alerts" {
  name = "GuardianAI-Alerts"
}

# 3. IAM Role for Lambda
resource "aws_iam_role" "lambda_exec_role" {
  name = "GuardianAI_Lambda_Role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# 4. Attach the IAM Policy (Points to your JSON file)
resource "aws_iam_role_policy" "guardian_policy" {
  name   = "GuardianAI_Policy"
  role   = aws_iam_role.lambda_exec_role.id
  policy = file("${path.module}/iam_policy.json")
}

# 5. The Lambda Function
resource "aws_lambda_function" "guardian_ai" {
  filename      = "lambda_function.zip" # Created during deployment
  function_name = "GuardianAI_Auditor"
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.security_alerts.arn
    }
  }
}

# 6. EventBridge Rule (Points to your Pattern file)
resource "aws_cloudwatch_event_rule" "security_group_watch" {
  name          = "GuardianAI_Security_Watch"
  description   = "Monitor Security Group changes"
  event_pattern = file("${path.module}/event_pattern.json")
}

# 7. Set Lambda as Target for EventBridge
resource "aws_cloudwatch_event_target" "sns" {
  rule      = aws_cloudwatch_event_rule.security_group_watch.name
  target_id = "SendToLambda"
  arn       = aws_lambda_function.guardian_ai.arn
}

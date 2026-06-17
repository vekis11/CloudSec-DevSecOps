output "api_gateway_url" {
  value = "${aws_api_gateway_stage.prod.invoke_url}/health"
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.items.name
}

output "lambda_function_name" {
  value = aws_lambda_function.api.function_name
}

output "github_actions_role_arn" {
  value       = aws_iam_role.github_actions.arn
  description = "Set as AWS_ROLE_ARN in GitHub secrets"
}

output "s3_artifacts_bucket" {
  value = aws_s3_bucket.artifacts.id
}

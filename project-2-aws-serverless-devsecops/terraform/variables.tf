variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "serverless-devsecops"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "github_org" {
  type = string
}

variable "github_repo" {
  type    = string
  default = "serverless-devsecops-demo"
}

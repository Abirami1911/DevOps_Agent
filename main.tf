
provider "aws" { region = "us-east-1" }

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  tags = { Name = "ai-payment-gateway-vpc" }
}

resource "aws_ecs_task_definition" "app" {
  family                   = "ai-payment-gateway-task"
  cpu                      = "256"
  memory                   = "512"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  container_definitions = jsonencode([
    {
      name      = "ai-payment-gateway-container"
      image     = "123456789.dkr.ecr.us-east-1.amazonaws.com/ai-payment-gateway:latest"
      cpu       = 256
      memory    = 512
      essential = true
    }
  ])
}

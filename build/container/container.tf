variable "branch" {
  default = "master"
}

variable "image" {
  type = string
  # must be passed after the ecr push in a prior build step
}

# gotta provide some info on how to use aws
provider "aws" {
  version = "~> 2.0"
  region  = "us-east-1"
}

# the container that's actually going to run our stuff
resource "aws_ecs_cluster" "repiece_cluster" {
  name = "repiece-cluster${var.branch}"
}

resource "aws_ecs_task_definition" "repiece_task_definition" {
  family                   = "repiece-task-${var.branch}"
  network_mode             = "awsvpc"
  task_role_arn            = aws_iam_role.iam_role_for_repiece_container.arn
  execution_role_arn       = aws_iam_role.iam_role_for_repiece_container.arn
  container_definitions    = <<DEFINITION
[{
    "name": "repiece",
    "image": "${var.image}",
    "logConfiguration": { 
        "logDriver": "awslogs",
        "options": { 
            "awslogs-group" : "${aws_cloudwatch_log_group.repiece.name}",
            "awslogs-region": "us-east-1",
            "awslogs-stream-prefix": "repiece/"
        }
    },
    "cpu": 0,
    "memory": 512,
    "essential": true,
    "environment" : [
        {"name": "file", "value" : "None"}
    ],
    "command": [
        "/bin/sh",
        "-c",
        "python3 /usr/src/repiece.py"
    ]
}]
DEFINITION
  requires_compatibilities = ["FARGATE"]
  memory                   = 512
  cpu                      = 256
}

resource "aws_cloudwatch_log_group" "repiece" {
  name              = "ecs/repiece-${var.branch}"
  retention_in_days = 7
}


###############################################################################
# container iam resources
###############################################################################

resource "aws_iam_role" "iam_role_for_repiece_container" {
  name               = "repiece_${var.branch}_role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_policy" "iam_policy_for_repiece_container" {
  name        = "repiece_${var.branch}_policy"
  path        = "/"
  description = "the policy used by the repiece container for branch ${var.branch}"
  policy      = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "s3:*",
        "logs:*",
        "ecr:*"
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "ecr_role_policy_attachment" {
  role       = "${aws_iam_role.iam_role_for_repiece_container.name}"
  policy_arn = "${aws_iam_policy.iam_policy_for_repiece_container.arn}"
}

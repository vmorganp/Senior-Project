# the variable that says what branch it's building
# this is useful for running test builds in the future
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

terraform {
  backend "s3"{
    region = "us-east-1"
  }
}


###############################################################################
###############################################################################
# Container code and associated IAM
###############################################################################
###############################################################################

# the container that's actually going to run our stuff
resource "aws_ecs_cluster" "repiece_cluster"{
  name = "repiece-cluster${var.branch}"
}

resource "aws_ecs_task_definition" "repiece_task_definition"{
  family = "repiece-task-${var.branch}"
  network_mode = "awsvpc"
  task_role_arn = aws_iam_role.iam_role_for_repiece_container.arn
  execution_role_arn = aws_iam_role.iam_role_for_repiece_container.arn
    container_definitions    = <<DEFINITION
[{
    "name": "handler",
    "image": "${var.image}",
    "logConfiguration": { 
        "logDriver": "awslogs",
        "options": { 
            "awslogs-group" : "/ecs/repiece-task-${var.branch}",
            "awslogs-region": "us-east-1",
            "awslogs-stream-prefix": "ecs"
        }
    },
    "cpu": 0,
    "memory": 512,
    "essential": true,
    "environment" : [
        {"name": "payload", "value" : "None"}
    ],
    "command": [
        "/bin/sh",
        "-c",
        "python3 /usr/src/app/handler.py"
    ]
}]
DEFINITION
  requires_compatibilities = ["FARGATE"]
  memory                   = 512
  cpu                      = 256
}



###############################################################################
# container iam resources
###############################################################################

resource "aws_iam_role" "iam_role_for_repiece_container" {
  name = "repiece_${var.branch}_role"
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
  policy = <<EOF
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

###############################################################################
###############################################################################
# s3 configuration and testing/force file structure objects
###############################################################################
###############################################################################

# the bucket that's going to hold all of our stuff
resource "aws_s3_bucket" "website_bucket" {
  bucket = "repiece-${var.branch}"
  acl    = "public-read"
  
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }

  website {
    index_document = "index.html"
  }

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Id": "IcanSayWhateverIWantHere",
  "Statement": [
      {
          "Sid": "Stmt1587618241826",
          "Effect": "Allow",
          "Principal": "*",
          "Action": "s3:GetObject",
          "Resource": "arn:aws:s3:::repiece-master/index.html"
      },
      {
          "Sid": "123",
          "Effect": "Allow",
          "Principal": {
              "AWS": "arn:aws:iam::573925394054:root"
          },
          "Action": "s3:*",
          "Resource": [
              "arn:aws:s3:::repiece-master",
              "arn:aws:s3:::repiece-master/*"
          ]
      }
  ]
}
EOF
}

resource "aws_s3_bucket_object" "webpage" {
  bucket = aws_s3_bucket.website_bucket.bucket
  key    = "/index.html"
  source = "index.html"
  etag = filemd5("index.html")
  content_type = "text/html"
}

resource "aws_s3_bucket_object" "uploads" {
  bucket = aws_s3_bucket.website_bucket.bucket
  key    = "/uploads/test3.jpg"
  source = "testFiles/test3.jpg"
  etag = filemd5("testFiles/test3.jpg")
}

resource "aws_s3_bucket_object" "outputs" {
  bucket = aws_s3_bucket.website_bucket.bucket
  key    = "/outputs/test3.jpg"
  source = "testFiles/test3.jpg"
  etag = filemd5("testFiles/test3.jpg")
}


###############################################################################
###############################################################################
# The cloudwatch pieces to setup events between the bucket and the ecs task
###############################################################################
###############################################################################

resource "aws_cloudwatch_event_rule" "capture_s3_updates"{
  name = "repiece_capture_s3_updates_${var.branch}"
  description = "capture updates to ${aws_s3_bucket.website_bucket.bucket} and send to repiece-${var.branch}"
  event_pattern = <<PATTERN
{
  "source": [
      "aws.s3"
  ],
  "detail-type": [
      "AWS API Call via CloudTrail"
  ],
  "detail": {
    "eventSource": [
      "s3.amazonaws.com"
    ],
    "eventName": [
      "PutObject"
    ],
    "requestParameters": {
      "bucketName": [
        "${aws_s3_bucket.website_bucket.bucket}"
      ],
      "key": [
        "uploads/*"
      ]
    }
  }
}
PATTERN
}

resource "aws_cloudwatch_event_target" "pass_uploads_to_container" {
  rule      = aws_cloudwatch_event_rule.capture_s3_updates.name
  target_id = "invoke_repiece_${var.branch}_container"
  arn       = aws_ecs_cluster.repiece_cluster.arn
  role_arn  = aws_iam_role.ecs_events.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = "${aws_ecs_task_definition.repiece_task_definition.arn}"
    launch_type = "FARGATE"
    network_configuration {
      subnets = [aws_subnet.main.id]
      security_groups = [aws_security_group.allow_out.id]
      assign_public_ip = true
    }
  }

  //TODO maybe need to add overrides in here
}

resource "aws_iam_role" "ecs_events" {
  name = "ecs_events"

  assume_role_policy = <<DOC
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "events.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
DOC
}

resource "aws_iam_role_policy" "ecs_events_run_task_with_any_role" {
  name = "ecs_events_run_task_with_any_role"
  role = aws_iam_role.ecs_events.id

  policy = <<DOC
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": "ecs:RunTask",
            "Resource": "*"
        }
    ]
}
DOC
}


###############################################################################
###############################################################################
# networking
###############################################################################
###############################################################################

resource "aws_vpc" "main"{
  cidr_block = "10.0.0.0/24"
}

resource "aws_subnet" "main" {
  vpc_id     = "${aws_vpc.main.id}"
  cidr_block = "10.0.0.0/24"

  tags = {
    Name = "${var.branch} Main"
  }
}

resource "aws_security_group" "allow_out" {
  name        = "allow_out"
  description = "Allow outbound traffic from contianer"
  vpc_id      = "${aws_vpc.main.id}"

  egress {
    description = "anything out"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

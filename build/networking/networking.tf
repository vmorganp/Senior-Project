variable "branch" {
  default = "master"
}

# gotta provide some info on how to use aws
provider "aws" {
  version = "~> 2.0"
  region  = "us-east-1"
}


resource "aws_default_vpc" "main" {
  tags = {
    Name = "Default VPC"
  }
}

resource "aws_default_subnet" "main" {
  availability_zone = "us-east-1a"

  tags = {
    Name = "${var.branch} Main"
  }
}


resource "aws_security_group" "allow_out" {
  name        = "allow_out"
  description = "Allow outbound traffic from contianer"
  vpc_id      = "${aws_default_vpc.main.id}"

  egress {
    description = "anything out"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

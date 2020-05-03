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


module "networking" {
  source = "./networking"
  branch = var.branch
}


module "storage" {
  source = "./storage"
  branch = var.branch
}


module "compute" {
  source = "./container"
  branch = var.branch
  image = var.image
}
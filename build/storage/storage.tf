variable "branch" {
  default = "master"
}

# gotta provide some info on how to use aws
provider "aws" {
  version = "~> 2.0"
  region  = "us-east-1"
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
            "Sid": "Stmt15876182241826",
            "Effect": "Allow",
            "Principal": "*",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": [
                "arn:aws:s3:::repiece-master/uploads/*",
                "arn:aws:s3:::repiece-master/outputs/*"
            ]
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
  bucket       = aws_s3_bucket.website_bucket.bucket
  key          = "/index.html"
  source = "${path.module}/index.html"
  content_type = "text/html"
}

resource "aws_s3_bucket_object" "uploads" {
  bucket = aws_s3_bucket.website_bucket.bucket
  key    = "/uploads/test4.jpg"
  source = "${path.module}/index.html"
}

resource "aws_s3_bucket_object" "outputs" {
  bucket = aws_s3_bucket.website_bucket.bucket
  key    = "/outputs/test3.jpg"
  source = "${path.module}/index.html"
}

# the variable that says what branch it's building
# this is useful for running test builds in the future
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
# Lambda function, layer, and iam resources
###############################################################################
###############################################################################

# the lambda that's actually going to run our stuff
resource "aws_lambda_function" "repiece" {
  filename      = "docScanner.py"
  function_name = "repiece-${var.branch}"
  role          = aws_iam_role.iam_role_for_repiece_lambda.arn
  handler       = "docScanner.main"
  source_code_hash = filebase64sha256("docScanner.py")
  runtime = "python3.7"
  memory_size = 128 # this is going to need a bump...I guarantee it
}

resource "aws_iam_role" "iam_role_for_repiece_lambda" {
  name = "repiece_${var.branch}_role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_policy" "iam_policy_for_repiece_lambda" {
  name        = "repiece_${var.branch}_policy"
  path        = "/"
  description = "the policy used by the repiece lambda for branch ${var.branch}"
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "s3:*"
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}
EOF
}

data "external" "layer_zipper"{
  program =["bash", "layer_zipper.sh"]
}

resource "aws_lambda_layer_version" "dependency_layer" {
  filename = "repiece_layer.zip"
  layer_name = "dependency_layer_repiece_${var.branch}"
  compatible_runtimes = ["${aws_lambda_function.repiece.runtime}"]
  # this is a hack that makes it wait on the layer to be zipped before it tries to deploy the layer
  description = "${"data.external.layer_zipper.result.success"}ly updated the lambda layer for ${var.branch}"
}



###############################################################################
###############################################################################
# s3 configuration and testing/force file structure objects
###############################################################################
###############################################################################

# the bucket that's going to hold all of our stuff
resource "aws_s3_bucket" "website_bucket" {
  bucket = "repiece_${var.branch}"
  acl    = "public-read-write"
  
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST"]
    allowed_origins = ["https://repiece_${var.branch}"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }

  website {
    index_document = "index.html"
  }

  # policy = #not sure what goes here just yet
}

resource "aws_s3_bucket_object" "webpage" {
  bucket = aws_s3_bucket.website_bucket
  key    = "/index.html"
  source = "index.html"
  etag = filemd5("index.html")
}

resource "aws_s3_bucket_object" "uploads" {
  bucket = aws_s3_bucket.website_bucket
  key    = "/uploads/test3.jpg"
  source = "testfiles/test3.jpg"
  etag = filemd5("testFiles/test3.jpg")
}

resource "aws_s3_bucket_object" "outputs" {
  bucket = aws_s3_bucket.website_bucket
  key    = "/outputs/test3.jpg"
  source = "testfiles/test3.jpg"
  etag = filemd5("testFiles/test3.jpg")
}


###############################################################################
###############################################################################
# The cloudwatch pieces to setup events between the bucket and the lambda
###############################################################################
###############################################################################

resource "aws_cloudwatch_event_rule" "capture_s3_updates"{
  name = "repiece_capture_s3_updates_${var.branch}"
  description = "capture updates to s3 bucket: ${aws_s3_bucket.website_bucket} and send to lambda: ${aws_lambda_function.repiece}"
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
        "${aws_s3_bucket.website_bucket}"
      ]
    }
  }
}
PATTERN
}

resource "aws_cloudwatch_event_target" "pass_uploads_to_lambda" {
  rule      = aws_cloudwatch_event_rule.capture_s3_updates.name
  target_id = "invoke_repiece_${var.branch}_lambda"
  arn       = aws_lambda_function.repiece.arn
}

resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "Allow_cloudwatch_execute_repiece_${var.branch}"
  action        = "lambda:InvokeFunction"
  function_name =  aws_lambda_function.repiece.function_name
  principal     = "events.amazonaws.com"
  source_arn    = "arn:aws:events:eu-west-1:573925394054:*" #TODO scope this better
}


// TODO networking? 

resource "aws_s3_bucket" "bad" {
  bucket = "bad-bucket"
  acl    = "public-read"
}

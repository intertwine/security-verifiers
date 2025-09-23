package lib.terraform

# S3 bucket encryption checks
s3_has_encryption(doc) {
    doc.resource.aws_s3_bucket[_].server_side_encryption_configuration[_]
}

# S3 bucket versioning checks
s3_has_versioning(doc) {
    doc.resource.aws_s3_bucket[_].versioning[_].enabled == true
}

# S3 bucket public access checks
s3_is_public(doc) {
    doc.resource.aws_s3_bucket[_].acl == "public-read"
}

s3_is_public(doc) {
    doc.resource.aws_s3_bucket[_].acl == "public-read-write"
}

s3_is_public(doc) {
    doc.resource.aws_s3_bucket[_].public_access_block[_].block_public_acls == false
}

# RDS encryption checks
rds_has_encryption(doc) {
    doc.resource.aws_db_instance[_].storage_encrypted == true
}

# RDS password policy checks
rds_has_weak_password(doc) {
    db := doc.resource.aws_db_instance[_]
    not db.password
    not db.manage_master_user_password
}

# Security group checks
sg_allows_all_traffic(doc) {
    sg := doc.resource.aws_security_group[_]
    sg.ingress[_].cidr_blocks[_] == "0.0.0.0/0"
    sg.ingress[_].from_port == 0
    sg.ingress[_].to_port == 0
}

sg_allows_all_traffic(doc) {
    sg := doc.resource.aws_security_group[_]
    sg.ingress[_].cidr_blocks[_] == "::/0"
    sg.ingress[_].from_port == 0
    sg.ingress[_].to_port == 0
}

# Secrets detection
has_hardcoded_secret(doc) {
    val := doc.variable[_].default
    contains(lower(val), "password")
}

has_hardcoded_secret(doc) {
    val := doc.variable[_].default
    contains(lower(val), "secret")
}

has_hardcoded_secret(doc) {
    val := doc.variable[_].default
    contains(lower(val), "token")
}

has_hardcoded_secret(doc) {
    val := doc.variable[_].default
    contains(lower(val), "key")
}

has_hardcoded_secret(doc) {
    val := doc.variable[_].default
    regex.match("[A-Za-z0-9+/]{20,}", val)  # Base64-like patterns
}

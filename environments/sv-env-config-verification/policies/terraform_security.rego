package security

import data.lib.terraform

# Terraform-specific security checks
deny[msg] {
    input.resource[_].aws_s3_bucket[_]
    not terraform.s3_has_encryption(input)
    msg := {
        "id": "TF_001",
        "message": "S3 bucket does not have server-side encryption enabled",
        "severity": "HIGH",
        "file": "terraform_config",
        "category": "encryption"
    }
}

deny[msg] {
    input.resource[_].aws_s3_bucket[_]
    not terraform.s3_has_versioning(input)
    msg := {
        "id": "TF_002",
        "message": "S3 bucket does not have versioning enabled",
        "severity": "MEDIUM",
        "file": "terraform_config",
        "category": "data-protection"
    }
}

deny[msg] {
    input.resource[_].aws_s3_bucket[_]
    terraform.s3_is_public(input)
    msg := {
        "id": "TF_003",
        "message": "S3 bucket has public access",
        "severity": "CRITICAL",
        "file": "terraform_config",
        "category": "access-control"
    }
}

deny[msg] {
    input.resource[_].aws_db_instance[_]
    not terraform.rds_has_encryption(input)
    msg := {
        "id": "TF_004",
        "message": "RDS instance does not have encryption enabled",
        "severity": "HIGH",
        "file": "terraform_config",
        "category": "encryption"
    }
}

deny[msg] {
    input.resource[_].aws_db_instance[_]
    terraform.rds_has_weak_password(input)
    msg := {
        "id": "TF_005",
        "message": "RDS instance uses weak password policy",
        "severity": "MEDIUM",
        "file": "terraform_config",
        "category": "authentication"
    }
}

deny[msg] {
    input.resource[_].aws_security_group[_]
    terraform.sg_allows_all_traffic(input)
    msg := {
        "id": "TF_006",
        "message": "Security group allows all inbound traffic",
        "severity": "CRITICAL",
        "file": "terraform_config",
        "category": "network-security"
    }
}

deny[msg] {
    input.variable[_]
    terraform.has_hardcoded_secret(input)
    msg := {
        "id": "TF_007",
        "message": "Terraform configuration contains hardcoded secrets",
        "severity": "CRITICAL",
        "file": "terraform_config",
        "category": "secrets-management"
    }
}

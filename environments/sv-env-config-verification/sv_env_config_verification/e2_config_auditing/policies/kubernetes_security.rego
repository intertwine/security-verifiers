package security

import data.lib.kubernetes

# Main deny rule that aggregates all security violations
deny[msg] if {
    input.kind == "Pod"
    kubernetes.has_insecure_capabilities(input)
    msg := {
        "id": "K8S_001",
        "message": "Pod has insecure capabilities",
        "severity": "HIGH",
        "file": input.metadata.name,
        "category": "security"
    }
}

deny[msg] if {
    input.kind == "Pod"
    kubernetes.has_privileged_container(input)
    msg := {
        "id": "K8S_002",
        "message": "Pod runs privileged containers",
        "severity": "CRITICAL",
        "file": input.metadata.name,
        "category": "security"
    }
}

deny[msg] if {
    input.kind == "Pod"
    kubernetes.has_host_path_volume(input)
    msg := {
        "id": "K8S_003",
        "message": "Pod uses hostPath volumes",
        "severity": "MEDIUM",
        "file": input.metadata.name,
        "category": "security"
    }
}

deny[msg] if {
    input.kind == "Service"
    kubernetes.exposes_sensitive_port(input)
    msg := {
        "id": "K8S_004",
        "message": "Service exposes sensitive port",
        "severity": "MEDIUM",
        "file": input.metadata.name,
        "category": "security"
    }
}

deny[msg] if {
    input.kind == "ConfigMap"
    kubernetes.contains_sensitive_data(input)
    msg := {
        "id": "K8S_005",
        "message": "ConfigMap may contain sensitive data",
        "severity": "LOW",
        "file": input.metadata.name,
        "category": "security"
    }
}

# General security checks
deny[msg] if {
    input.apiVersion
    not kubernetes.has_resource_limits(input)
    msg := {
        "id": "GEN_001",
        "message": "Resource does not have CPU/memory limits defined",
        "severity": "MEDIUM",
        "file": input.metadata.name,
        "category": "resource-management"
    }
}

deny[msg] if {
    input.apiVersion
    kubernetes.has_default_namespace(input)
    msg := {
        "id": "GEN_002",
        "message": "Resource uses default namespace",
        "severity": "LOW",
        "file": input.metadata.name,
        "category": "best-practices"
    }
}

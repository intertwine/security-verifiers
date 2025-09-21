package lib.kubernetes

# Check if a pod has insecure capabilities
has_insecure_capabilities(pod) if {
    pod.spec.containers[_].securityContext.capabilities.add[_] == "SYS_ADMIN"
}

has_insecure_capabilities(pod) if {
    pod.spec.containers[_].securityContext.capabilities.add[_] == "NET_ADMIN"
}

# Check if a pod runs privileged containers
has_privileged_container(pod) if {
    pod.spec.containers[_].securityContext.privileged == true
}

# Check if a pod uses hostPath volumes
has_host_path_volume(pod) if {
    pod.spec.volumes[_].hostPath
}

# Check if a service exposes sensitive ports
exposes_sensitive_port(service) if {
    service.spec.ports[_].port == 22  # SSH
}

exposes_sensitive_port(service) if {
    service.spec.ports[_].port == 3389  # RDP
}

# Check if a ConfigMap contains sensitive data patterns
contains_sensitive_data(configmap) if {
    configmap.data[_] = val
    contains(lower(val), "password")
}

contains_sensitive_data(configmap) if {
    configmap.data[_] = val
    contains(lower(val), "secret")
}

contains_sensitive_data(configmap) if {
    configmap.data[_] = val
    contains(lower(val), "token")
}

# Check if resource has CPU/memory limits
has_resource_limits(resource) if {
    resource.spec.template.spec.containers[_].resources.limits.cpu
    resource.spec.template.spec.containers[_].resources.limits.memory
}

has_resource_limits(resource) if {
    resource.spec.containers[_].resources.limits.cpu
    resource.spec.containers[_].resources.limits.memory
}

# Check if resource uses default namespace
has_default_namespace(resource) if {
    resource.metadata.namespace == "default"
}

has_default_namespace(resource) if {
    not resource.metadata.namespace
}

#!/usr/bin/env bash
#
# Clone recommended Kubernetes and Terraform repositories for E2 dataset building.
#
# Usage:
#   ./scripts/data/clone_e2_sources.sh [--k8s-only | --tf-only]
#
# Outputs:
#   - scripts/data/sources/kubernetes/  (K8s manifests)
#   - scripts/data/sources/terraform/   (Terraform modules)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCES_DIR="${SCRIPT_DIR}/sources"
K8S_DIR="${SOURCES_DIR}/kubernetes"
TF_DIR="${SOURCES_DIR}/terraform"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
CLONE_K8S=true
CLONE_TF=true

if [[ "${1:-}" == "--k8s-only" ]]; then
    CLONE_TF=false
elif [[ "${1:-}" == "--tf-only" ]]; then
    CLONE_K8S=false
fi

echo -e "${GREEN}E2 Source Repository Cloner${NC}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Ensure directories exist
mkdir -p "${K8S_DIR}" "${TF_DIR}"

# Clone Kubernetes sources
if [[ "${CLONE_K8S}" == "true" ]]; then
    echo -e "${YELLOW}Cloning Kubernetes sources...${NC}"

    # Official Kubernetes examples
    if [[ ! -d "${K8S_DIR}/examples" ]]; then
        echo "  → kubernetes/examples (official K8s examples)"
        git clone --depth 1 https://github.com/kubernetes/examples.git "${K8S_DIR}/examples" 2>&1 | grep -v "Receiving objects" || true
        echo -e "    ${GREEN}✓ Cloned${NC}"
    else
        echo -e "    ${GREEN}✓ Already exists: kubernetes/examples${NC}"
    fi

    # Google Cloud microservices demo
    if [[ ! -d "${K8S_DIR}/microservices-demo" ]]; then
        echo "  → GoogleCloudPlatform/microservices-demo"
        git clone --depth 1 https://github.com/GoogleCloudPlatform/microservices-demo.git "${K8S_DIR}/microservices-demo" 2>&1 | grep -v "Receiving objects" || true
        echo -e "    ${GREEN}✓ Cloned${NC}"
    else
        echo -e "    ${GREEN}✓ Already exists: microservices-demo${NC}"
    fi

    # ContainerSolutions minimal examples
    if [[ ! -d "${K8S_DIR}/kubernetes-examples" ]]; then
        echo "  → ContainerSolutions/kubernetes-examples"
        git clone --depth 1 https://github.com/ContainerSolutions/kubernetes-examples.git "${K8S_DIR}/kubernetes-examples" 2>&1 | grep -v "Receiving objects" || true
        echo -e "    ${GREEN}✓ Cloned${NC}"
    else
        echo -e "    ${GREEN}✓ Already exists: kubernetes-examples${NC}"
    fi

    echo ""
fi

# Clone Terraform sources
if [[ "${CLONE_TF}" == "true" ]]; then
    echo -e "${YELLOW}Cloning Terraform sources...${NC}"

    # AWS VPC module
    if [[ ! -d "${TF_DIR}/terraform-aws-vpc" ]]; then
        echo "  → terraform-aws-modules/terraform-aws-vpc"
        git clone --depth 1 https://github.com/terraform-aws-modules/terraform-aws-vpc.git "${TF_DIR}/terraform-aws-vpc" 2>&1 | grep -v "Receiving objects" || true
        echo -e "    ${GREEN}✓ Cloned${NC}"
    else
        echo -e "    ${GREEN}✓ Already exists: terraform-aws-vpc${NC}"
    fi

    # AWS EKS module
    if [[ ! -d "${TF_DIR}/terraform-aws-eks" ]]; then
        echo "  → terraform-aws-modules/terraform-aws-eks"
        git clone --depth 1 https://github.com/terraform-aws-modules/terraform-aws-eks.git "${TF_DIR}/terraform-aws-eks" 2>&1 | grep -v "Receiving objects" || true
        echo -e "    ${GREEN}✓ Cloned${NC}"
    else
        echo -e "    ${GREEN}✓ Already exists: terraform-aws-eks${NC}"
    fi

    # AWS RDS module
    if [[ ! -d "${TF_DIR}/terraform-aws-rds" ]]; then
        echo "  → terraform-aws-modules/terraform-aws-rds"
        git clone --depth 1 https://github.com/terraform-aws-modules/terraform-aws-rds.git "${TF_DIR}/terraform-aws-rds" 2>&1 | grep -v "Receiving objects" || true
        echo -e "    ${GREEN}✓ Cloned${NC}"
    else
        echo -e "    ${GREEN}✓ Already exists: terraform-aws-rds${NC}"
    fi

    echo ""
fi

# Summary
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Summary:${NC}"
echo ""

if [[ "${CLONE_K8S}" == "true" ]]; then
    K8S_COUNT=$(find "${K8S_DIR}" -type f \( -name "*.yaml" -o -name "*.yml" \) 2>/dev/null | wc -l | tr -d ' ')
    echo "  Kubernetes manifests: ${K8S_COUNT} files"
    echo "  Location: ${K8S_DIR}"
    echo ""
fi

if [[ "${CLONE_TF}" == "true" ]]; then
    TF_COUNT=$(find "${TF_DIR}" -type f -name "*.tf" 2>/dev/null | wc -l | tr -d ' ')
    echo "  Terraform files: ${TF_COUNT} files"
    echo "  Location: ${TF_DIR}"
    echo ""
fi

echo -e "${GREEN}Ready to build E2 datasets!${NC}"
echo ""
echo "Run:"
echo -e "  ${YELLOW}make data-e2 K8S_ROOT=${K8S_DIR} TF_ROOT=${TF_DIR}${NC}"
echo ""

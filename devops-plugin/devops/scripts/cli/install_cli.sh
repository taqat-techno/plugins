#!/bin/bash
#
# Azure DevOps CLI Installer for macOS/Linux
# Part of the DevOps Plugin for Claude Code
#
# Usage:
#   ./install_cli.sh [OPTIONS]
#
# Options:
#   -o, --organization NAME    Azure DevOps organization (default: TaqaTechno)
#   -p, --project NAME         Default project name (optional)
#   -t, --pat TOKEN            Personal Access Token
#   -s, --skip-cli             Skip Azure CLI installation
#   -h, --help                 Show this help
#
# Examples:
#   ./install_cli.sh -o TaqaTechno -p "Relief Center"
#   ./install_cli.sh -o TaqaTechno -t "your-pat-token"
#
# Author: TAQAT Techno
# Version: 2.0.0

set -e

# Default values
ORGANIZATION="TaqaTechno"
PROJECT=""
PAT=""
SKIP_CLI=false
SHELL_PROFILE=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Output functions
step() { echo -e "\n${GREEN}[✓]${NC} $1"; }
info() { echo -e "    ${CYAN}$1${NC}"; }
warn() { echo -e "    ${YELLOW}[!] $1${NC}"; }
err()  { echo -e "    ${RED}[X] $1${NC}"; }

# Help
show_help() {
    echo "Azure DevOps CLI Installer for macOS/Linux"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -o, --organization NAME    Azure DevOps organization (default: TaqaTechno)"
    echo "  -p, --project NAME         Default project name (optional)"
    echo "  -t, --pat TOKEN            Personal Access Token"
    echo "  -s, --skip-cli             Skip Azure CLI installation"
    echo "  -h, --help                 Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 -o TaqaTechno -p \"Relief Center\""
    echo "  $0 -o TaqaTechno -t \"your-pat-token\""
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--organization)
            ORGANIZATION="$2"
            shift 2
            ;;
        -p|--project)
            PROJECT="$2"
            shift 2
            ;;
        -t|--pat)
            PAT="$2"
            shift 2
            ;;
        -s|--skip-cli)
            SKIP_CLI=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            ;;
    esac
done

# Detect shell profile
detect_shell_profile() {
    if [[ -n "$ZSH_VERSION" ]] || [[ "$SHELL" == *"zsh"* ]]; then
        if [[ -f "$HOME/.zshrc" ]]; then
            SHELL_PROFILE="$HOME/.zshrc"
        else
            SHELL_PROFILE="$HOME/.zprofile"
        fi
    elif [[ -n "$BASH_VERSION" ]] || [[ "$SHELL" == *"bash"* ]]; then
        if [[ -f "$HOME/.bashrc" ]]; then
            SHELL_PROFILE="$HOME/.bashrc"
        else
            SHELL_PROFILE="$HOME/.bash_profile"
        fi
    else
        SHELL_PROFILE="$HOME/.profile"
    fi
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ -f /etc/debian_version ]]; then
        echo "debian"
    elif [[ -f /etc/redhat-release ]]; then
        echo "rhel"
    else
        echo "linux"
    fi
}

# Header
echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  AZURE DEVOPS CLI INSTALLER${NC}"
echo -e "${CYAN}  DevOps Plugin for Claude Code v2.0${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# ============================================
# PHASE 1: Check Prerequisites
# ============================================
step "Phase 1: Checking Prerequisites"

OS=$(detect_os)
info "Operating System: $OS"

detect_shell_profile
info "Shell Profile: $SHELL_PROFILE"

# Check for curl
if command -v curl &> /dev/null; then
    info "curl: Available"
else
    err "curl is required but not installed"
    exit 1
fi

# ============================================
# PHASE 2: Install Azure CLI
# ============================================
step "Phase 2: Checking Azure CLI"

AZ_INSTALLED=false

if command -v az &> /dev/null; then
    AZ_VERSION=$(az --version 2>&1 | grep "azure-cli" | awk '{print $2}')
    info "Azure CLI already installed: $AZ_VERSION"
    AZ_INSTALLED=true
fi

if [[ "$AZ_INSTALLED" == "false" ]] && [[ "$SKIP_CLI" == "false" ]]; then
    info "Installing Azure CLI..."

    case $OS in
        macos)
            # macOS: Use Homebrew
            if command -v brew &> /dev/null; then
                info "Using Homebrew to install Azure CLI..."
                brew update
                brew install azure-cli
            else
                warn "Homebrew not found. Installing via script..."
                curl -L https://aka.ms/InstallAzureCli | bash
            fi
            ;;

        debian)
            # Debian/Ubuntu
            info "Installing Azure CLI on Debian/Ubuntu..."
            curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
            ;;

        rhel)
            # RHEL/CentOS/Fedora
            info "Installing Azure CLI on RHEL/Fedora..."
            sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
            sudo dnf install -y https://packages.microsoft.com/config/rhel/8/packages-microsoft-prod.rpm
            sudo dnf install -y azure-cli
            ;;

        *)
            # Generic Linux
            info "Installing Azure CLI via pip..."
            if command -v pip3 &> /dev/null; then
                pip3 install azure-cli
            elif command -v pip &> /dev/null; then
                pip install azure-cli
            else
                err "pip not found. Please install Azure CLI manually."
                exit 1
            fi
            ;;
    esac

    AZ_INSTALLED=true
fi

# Verify Azure CLI
if command -v az &> /dev/null; then
    AZ_VERSION=$(az --version 2>&1 | grep "azure-cli" | awk '{print $2}')
    info "Azure CLI Version: $AZ_VERSION"
else
    err "Azure CLI verification failed"
    exit 1
fi

# ============================================
# PHASE 3: Install DevOps Extension
# ============================================
step "Phase 3: Installing Azure DevOps Extension"

# Check if extension is installed
EXT_INSTALLED=false
EXT_INFO=$(az extension show --name azure-devops 2>&1) || true

if [[ "$EXT_INFO" != *"not installed"* ]] && [[ "$EXT_INFO" != *"error"* ]]; then
    EXT_VERSION=$(echo "$EXT_INFO" | grep -o '"version": "[^"]*"' | cut -d'"' -f4)
    info "DevOps extension already installed: $EXT_VERSION"
    EXT_INSTALLED=true

    # Check for updates
    info "Checking for updates..."
    az extension update --name azure-devops 2>/dev/null || true
fi

if [[ "$EXT_INSTALLED" == "false" ]]; then
    info "Installing azure-devops extension..."
    az extension add --name azure-devops --yes
    info "Azure DevOps extension installed successfully"
fi

# Verify extension
EXT_INFO=$(az extension show --name azure-devops 2>&1)
EXT_VERSION=$(echo "$EXT_INFO" | grep -o '"version": "[^"]*"' | cut -d'"' -f4)
info "Extension Version: $EXT_VERSION"

# ============================================
# PHASE 4: Configure Defaults
# ============================================
step "Phase 4: Configuring Defaults"

ORG_URL="https://dev.azure.com/$ORGANIZATION"
info "Setting organization: $ORG_URL"
az devops configure --defaults organization="$ORG_URL" 2>/dev/null

if [[ -n "$PROJECT" ]]; then
    info "Setting default project: $PROJECT"
    az devops configure --defaults project="$PROJECT" 2>/dev/null
fi

# Show current config
info "Current defaults:"
az devops configure --list 2>&1 | while read -r line; do
    info "  $line"
done

# ============================================
# PHASE 5: Configure Authentication
# ============================================
step "Phase 5: Configuring Authentication"

if [[ -n "$PAT" ]]; then
    info "Setting PAT as environment variables..."

    # Add to shell profile
    {
        echo ""
        echo "# Azure DevOps CLI Authentication (added by install_cli.sh)"
        echo "export AZURE_DEVOPS_EXT_PAT=\"$PAT\""
        echo "export ADO_PAT_TOKEN=\"$PAT\""
        echo "export DEVOPS_HYBRID_MODE=\"true\""
    } >> "$SHELL_PROFILE"

    # Set for current session
    export AZURE_DEVOPS_EXT_PAT="$PAT"
    export ADO_PAT_TOKEN="$PAT"
    export DEVOPS_HYBRID_MODE="true"

    info "Set AZURE_DEVOPS_EXT_PAT (for CLI)"
    info "Set ADO_PAT_TOKEN (for MCP)"
    info "Set DEVOPS_HYBRID_MODE=true"
    info "Added to: $SHELL_PROFILE"

else
    warn "No PAT provided. You can set it later by adding to $SHELL_PROFILE:"
    info '  export AZURE_DEVOPS_EXT_PAT="your-pat"'
    info '  export ADO_PAT_TOKEN="your-pat"'
    info '  export DEVOPS_HYBRID_MODE="true"'
    info ""
    info "Or login interactively:"
    info "  az devops login --organization $ORG_URL"
fi

# ============================================
# PHASE 6: Validation
# ============================================
step "Phase 6: Validating Installation"

VALIDATION_PASSED=true

if [[ -n "$PAT" ]] || [[ -n "$AZURE_DEVOPS_EXT_PAT" ]]; then
    info "Testing CLI connection..."
    if PROJECTS=$(az devops project list --output json 2>&1); then
        PROJECT_COUNT=$(echo "$PROJECTS" | grep -o '"name"' | wc -l)
        info "Connection successful: $PROJECT_COUNT projects found"

        # List first few projects
        echo "$PROJECTS" | grep -o '"name": "[^"]*"' | head -3 | while read -r line; do
            PROJECT_NAME=$(echo "$line" | cut -d'"' -f4)
            info "  - $PROJECT_NAME"
        done
    else
        warn "CLI connection test failed. Please verify your PAT token."
        VALIDATION_PASSED=false
    fi
else
    warn "Skipping connection test (no PAT configured)"
fi

# ============================================
# Summary
# ============================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  INSTALLATION COMPLETE${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

echo -e "${CYAN}CLI Status:${NC}"
echo "  Azure CLI:        Installed ($AZ_VERSION)"
echo "  DevOps Extension: Installed ($EXT_VERSION)"
echo "  Organization:     $ORGANIZATION"
if [[ -n "$PROJECT" ]]; then
    echo "  Default Project:  $PROJECT"
fi

echo ""
echo -e "${CYAN}Authentication:${NC}"
if [[ -n "$PAT" ]]; then
    echo "  AZURE_DEVOPS_EXT_PAT: Configured"
    echo "  ADO_PAT_TOKEN:        Configured"
    echo "  DEVOPS_HYBRID_MODE:   Enabled"
else
    echo -e "  ${YELLOW}Status: Not configured (set PAT to enable)${NC}"
fi

echo ""
echo -e "${CYAN}Next Steps:${NC}"
if [[ -z "$PAT" ]]; then
    echo "  1. Set your PAT token (see instructions above)"
fi
echo "  2. Reload shell profile: source $SHELL_PROFILE"
echo "  3. Configure MCP server in Claude Code settings"
echo "  4. Restart Claude Code"
echo "  5. Test with: az devops project list"
echo ""

# Return status
if [[ "$VALIDATION_PASSED" == "true" ]]; then
    exit 0
else
    exit 1
fi

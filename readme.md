# LoStack - Local Containerized Service Stack for MacOS

![LoStack Dashboard](docs/images/dashboard.png?raw=true "LoStack Dashboard")

A comprehensive containerized service stack designed to run locally on MacOS using Ubuntu Server in a VM. Outside of the MacOS instructions, there is nothing really MacOS specific. This stack can also be run on WSL/WSL2, or directly on most Docker-capable Linux hosts. LoStack provides a complete development environment with automatic SSL certificates, authentication, service discovery, and on-demand container management.

![Sablier UI](docs/images/sablier-admin.png?raw=true "Sablier UI")

LoStack comes with a custom app called Sablier UI for configuring container auto-start. It generates necessary files for Traefik to handle the auto-start.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Services](#services)
- [Network Configuration](#network-configuration)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)
- [Contributing](#contributing)
- [License](#license)

## Overview

After a decade away from MacOS, Docker Desktop proved inadequate for running complex containerized service stacks. LoStack solves this by leveraging UTM (QEMU wrapper) with Ubuntu Server to create a robust local development environment that rivals cloud-based solutions.

## Features

- **Automatic Service Discovery**: CoreDNS handles local DNS resolution
- **SSL Certificates**: Self-signed certificates via mkcert for secure local development
- **Centralized Authentication**: Authelia with OpenLDAP backend for SSO across all services
- **Reverse Proxy**: Traefik with automatic HTTPS and service routing
- **On-Demand Services**: Sablier manages container lifecycle, starting services when needed
- **Web-Based Management**: Homepage dashboard for easy service access
- **Development Tools**: Integrated Code-Server, file browsers, git service, and utilities
- **Resource Efficient**: Services sleep when not in use to conserve system resources

## Architecture

```
MacOS Host
├── UTM (QEMU Hypervisor)
│   └── Ubuntu Server VM
│       ├── Docker Engine
│       ├── Docker Compose
│       └── Service Stack
│           ├── Traefik (Reverse Proxy)
│           ├── Authelia (Authentication)
│           ├── OpenLDAP (User Directory)
│           ├── CoreDNS (DNS Resolution)
│           ├── Sablier (Container Management)
│           └── Application Services
```

## Prerequisites

- **MacOS**: Recent version with sufficient RAM (8GB+ recommended)
- **UTM**: Download from https://mac.getutm.app/
- **Ubuntu Server ISO**: Latest LTS version recommended
- **Network**: Static IP configuration preferred
- **Knowledge**: Basic familiarity with Docker, command line, and networking

## Installation

### Step 1: Virtual Machine Setup

1. **Install UTM** from https://mac.getutm.app/
2. **Download Ubuntu Server ISO** from https://ubuntu.com/download/server
3. **Create VM in UTM**:
   - Allocate 4GB+ RAM
   - 40GB+ disk space
   - **Important**: Set network mode to "Bridge"
4. **Install Ubuntu Server**:
   - Set hostname to `lostack.internal`
   - Enable SSH server
   - **Do not install Docker via snap** (causes compatibility issues)

### Step 2: System Configuration

SSH into your VM or use UTM console:

```bash
# Navigate to docker directory
sudo mkdir /docker && cd /docker

# Clone the repository
git clone https://github.com/AndrewSpangler/lostack .

# Run setup script (installs Docker and dependencies)
sudo bash ./setup-ubuntu.sh

# Make environment file editable
sudo chmod 666 .env

# Clone Sablier Traefik plugin repository
cd plugins-local/src/github.com/ && sudo mkdir sablierapp && cd sablierapp
git clone https://github.com/SablierApp/sablier
```

### Step 3: Environment Configuration

Edit the `.env` file with your specific settings:

```bash
nano .env
```

**Critical variables to configure**:
- `HOST_IP`: Your VM's IP address (cannot be localhost/127.0.0.1)
- `DNS_IP`: Your primary DNS server (usually router IP)
- `ADMIN_PASSWORD`: Master password for OpenLDAP
- `DATABASE_PASSWORD`: Password for database services
- Generate secure random strings for Authelia secrets

### Step 4: Initial Deployment

```bash
# Start services (CoreDNS will initially fail - expected)
sudo docker compose up -d

# Replace systemd-resolved with CoreDNS
sudo systemctl stop systemd-resolved
sudo systemctl disable systemd-resolved

# Restart CoreDNS
sudo docker compose stop coredns
sudo docker compose up coredns -d

# Verify CoreDNS is running on port 53
sudo lsof -i -P | grep ":53"
```

### Step 5: Authentication Setup

1. Open `http://[VM-IP]:8785/setup` in your browser
2. Enter the configuration password from your `.env` file
3. Complete LDAP User Manager setup wizard
4. Create your first admin user

### Step 6: DNS Integration

Configure DNS on your MacOS host:
- **System Preferences** → **Network** → **Advanced** → **DNS**
- Add your VM's IP as a secondary DNS server
- For network-wide access, configure your router to use the VM as a secondary DNS

## Configuration

### Environment Variables

The stack uses a comprehensive `.env` file for configuration. Key sections include:

**Network Configuration**:
```bash
HOST_IP=192.168.1.64          # VM IP address
DNS_IP=192.168.1.1            # Primary DNS resolver
DOMAINNAME=lostack.internal   # Base domain
```

**Security**:
```bash
ADMIN_PASSWORD=your_secure_password
DATABASE_PASSWORD=your_db_password
AUTHELIA_JWT_SECRET=generated_secret
AUTHELIA_STORAGE_ENCRYPTION_KEY=generated_key
AUTHELIA_SESSION_SECRET=generated_secret
```

**Service Ports**:
```bash
TRAEFIK_PORT_HTTP=80
TRAEFIK_PORT_HTTPS=443
CODE_SERVER_PORT=8443
CORE_DNS_PORT=53
```

### Generating Secure Secrets

Use the included IT-Tools service to generate secure random strings:

```bash
# Temporarily expose IT-Tools (uncomment port mapping in docker-compose.yml)
sudo docker compose up it-tools -d

# Visit http://[VM-IP]:8380/token-generator
# Generate 32+ character strings for Authelia secrets
```

## Services

LoStack includes a comprehensive suite of services:

### Core Services

| Service | Purpose | Access URL |
|---------|---------|------------|
| **Homepage** | Service dashboard | https://lostack.internal/ |
| **Traefik** | Reverse proxy | https://traefik.lostack.internal/ |
| **Authelia** | Authentication | https://authelia.lostack.internal/ |
| **LDAP User Manager** | User management | https://ldap-user-manager.lostack.internal/ |
| **Sablier GUI** | Container management | https://sablier-gui.lostack.internal/ |

### Development Tools

| Service | Purpose | Access URL |
|---------|---------|------------|
| **Code-Server** | Web-based VS Code | https://code-server.lostack.internal/ |
| **Dozzle** | Container logs | https://dozzle.lostack.internal/ |
| **Filebrowser** | File management | https://filebrowser.lostack.internal/ |
| **Gitea** | Git Service | https://gitea.lostack.internal |
| **Jupyter** | Python notebooks | https://jupyter.lostack.internal/ |

### Utility Applications

| Service | Purpose | Access URL |
|---------|---------|------------|
| **ByteStash** | Code snippets | https://bytestash.lostack.internal/ |
| **CyberChef** | Data manipulation | https://cyberchef.lostack.internal/ |
| **Excalidraw** | Diagramming | https://excalidraw.lostack.internal/ |
| **IT-Tools** | Developer utilities | https://it-tools.lostack.internal/ |
| **Tasks** | Todo management | https://tasks.lostack.internal/ |

### File Services

| Service | Purpose | Access URL |
|---------|---------|------------|
| **FileStash** | File transfers | https://filestash.lostack.internal/ |
| **PairDrop** | P2P file sharing | https://pairdrop.lostack.internal/ |
| **Serve** | Static file server | https://serve.lostack.internal/ |

### Conversion Tools

| Service | Purpose | Access URL |
|---------|---------|------------|
| **HRConvert** | File conversion | https://hrconvert.lostack.internal/ |
| **Morphos** | Batch conversion | https://morphos.lostack.internal/ |
| **Reubah** | Bulk file converter | https://reubah.lostack.internal/ |

## Network Configuration

### Port Mapping

| Port | Service | Description | Exposure |
|------|---------|-------------|----------|
| 53 | CoreDNS | DNS resolution | External |
| 80 | Traefik | HTTP (redirects to HTTPS) | External |
| 443 | Traefik | HTTPS traffic | External |
| 8443 | Code-Server | Emergency access | External (optional) |
| 8785 | LDAP User Manager | Initial setup | External (disable after setup) |

### DNS Configuration

LoStack replaces Ubuntu's systemd-resolved with CoreDNS to provide:
- Local domain resolution (*.lostack.internal)
- Automatic service discovery
- Clearer control over Docker Service DNS

## Auth Integration Table

Only containers with multi-user support are listed.

| Service | OpenLDAP | Auto Sign-In |
| Linkding | -> | Yes (Default) |
| Ldap User Manager | -> | Yes (Enable in ENV after setup) |
| Gitea | Yes (See setup guide) | Yes (WIP - not enabled yet) |
| FreshRSS | -> | Yes (See setup guide) |
| Filebrowser | -> | Yes (With some effort) (See https://github.com/hurlenko/filebrowser-docker/issues/48) |



## Usage

### Accessing Services

1. **Primary Access**: Visit https://lostack.internal/ for the main dashboard
2. **Direct Access**: Use service-specific URLs (e.g., https://code-server.lostack.internal/)
3. **Emergency Access**: Code-Server available at https://[VM-IP]:8443/

### Managing Containers

**Sablier GUI** provides container lifecycle management:
- Import the included `sablier-config.yml` for default settings
- Services automatically start when accessed via dashboard
- Containers sleep after configured inactivity period
- Monitor resource usage and container status

### User Management

**LDAP User Manager** handles authentication:
1. Access at https://ldap-user-manager.lostack.internal/
2. Create users and groups
3. Users automatically have access to all authenticated services
4. After initial setup, set `LUM_REMOTE_HTTP_HEADERS_LOGIN=true` for SSO

## Troubleshooting

### Common Issues

**CoreDNS fails to start on first run**:
- Expected behavior while systemd-resolved is active
- Follow Step 4 instructions to replace systemd-resolved

**Services not accessible from MacOS**:
- Verify VM IP is correctly set in `HOST_IP`
- Check DNS configuration on MacOS host
- Ensure UTM network mode is set to "Bridge"

**SSL certificate warnings**:
- Install mkcert certificates on MacOS host
- Copy certificates from `./certs/` directory
- Run `mkcert -install` on host system

**Container startup issues**:
- Check Docker Compose logs: `sudo docker compose logs [service-name]`
- Verify environment variables are correctly set
- Ensure sufficient system resources

### Log Locations

- **Traefik logs**: `./logs/traefik/`
- **Authelia logs**: `./config/authelia/authelia.log`
- **Container logs**: `sudo docker compose logs [service-name]`

### Performance Optimization

**For better performance**:
- Allocate more RAM to the VM (8GB+ recommended)
- Use SSD storage for VM disk
- Adjust Sablier timeout values based on usage patterns
- Monitor resource usage via Homepage widgets

## Advanced Configuration

### Custom Services

Add new services to `docker-compose.yml`:

```yaml
your-service:
  image: your-image
  container_name: your-service
  networks:
    - traefik_network
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.your-service.rule=Host(`your-service.${DOMAINNAME}`)"
    - "traefik.http.services.your-service.loadbalancer.server.port=PORT"
    - "homepage.name=Your Service"
    - "homepage.group=Apps"
    - "homepage.description=Service description"
    - "homepage.href=https://your-service.${DOMAINNAME}/"
    - "sablier.enable=true"
    - "sablier.group=your-service"
```

### Backup and Restore

**Backup essential data**:
```bash
# Backup configuration and data
tar -czf lostack-backup.tar.gz config/ appdata/ .env

# Backup LDAP data specifically
sudo docker compose exec openldap slapcat > ldap-backup.ldif
```

**Restore from backup**:
```bash
# Restore files
tar -xzf lostack-backup.tar.gz

# Restore LDAP data
sudo docker compose exec openldap slapadd -l ldap-backup.ldif
```

### Gitea OpenLDAP Integration

#### Access 
1. Access https://gitea.lostack.internal
2. Go to **Site Administration** (user icon → Site Administration)
3. Navigate to **Authentication Sources**
4. Click **Add Authentication Source**

#### Source Settings
| Field | Value |
|-------|-------|
| **Authentication Type** | `LDAP (via BindDN)` |
| **Authentication Name** | `OpenLDAP` |
| **Host** | `openldap` |
| **Port** | `389` |
| **Security Protocol** | `Unecrypted` |
| **Bind DN** | `cn=readonly,dc=lostack,dc=internal` |
| **Bind Password** | `readonly` |
| **User Search Base** | `ou=people,dc=lostack,dc=internal` |
| **User Filter** | `(&(objectClass=inetOrgPerson)(uid=%[1]s))` |
| **Username attribute** | `uid` |
| **First name attribute** | `givenName` |
| **Surname attribute** | `sn` |
| **Email attribute** | `mail` |
| **Admin Filter** | `(memberOf=cn=admins,ou=groups,dc=lostack,dc=internal)` |
| **Enable user synchronization** | `☑ Checked` |
| **This Authentication Source is Activated** | `☑ Checked` |

#### Group Verification (Optional)

If you enable this you will need to create a "gitea_users" group in Ldap User Manager

| Field | Value |
|-------|-------|
| **Group Search Base DN** | `ou=groups,dc=lostack,dc=internal` |
| **Group Attribute Containing List Of Users** | `memberUid` |
| **User Attribute Listed in Group** | `uid` |
| **Verify group membership in LDAP** | `(|(cn=gitea_users)(cn=developers)(cn=admins))` |

#### After Adding LDAP Authentication:
1. **Disable registration** in Site Administration → Configuration → Service Settings
2. **Test login** with an LDAP user

#### Troubleshooting Tips:
- Check Gitea logs: `sudo docker logs gitea`
- Verify LDAP structure matches the configuration
- Ensure groups exist in LDAP before using group filters

### FreshRSS OpenLDAP/SSO Integration

#### Config 
1. Access https://freshrss.lostack.internal and log in to FreshRSS with the admin credentials from .env
2. Go to https://freshrss.lostack.internal/i/?c=auth
3. Select "HTTP" in the **Authentication method** dropdown

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Test changes thoroughly
4. Submit a pull request with detailed description


## License

- **Sablier-GUI**: WTFPL - [Andrew Spangler](https://github.com/AndrewSpangler)
- **Bootstrap CSS/JS**: MIT - [The Bootstrap Authors](https://github.com/twbs/bootstrap/graphs/contributors)
- **Other components**: Licensed under their respective open-source licenses

## Support

For issues and support:
- Check the [Troubleshooting](#troubleshooting) section
- Review Docker Compose logs
- Open an issue on the GitHub repository
- Ensure all prerequisites are met before reporting issues

---

**Note**: This project is designed for local development environments. For production use, additional security hardening and monitoring should be implemented.
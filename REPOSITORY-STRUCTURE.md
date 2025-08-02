# 📁 Repository Structure

## 🎯 Clean, Production-Ready EC2 Deployment

This repository has been cleaned up to focus on the production-ready EC2 deployment solution.

## 📂 Core Application Files

| File | Purpose |
|------|---------|
| `app.py` | Main Flask application |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Docker container configuration |
| `.dockerignore` | Docker build exclusions |
| `field_definitions.json` | Field mapping definitions |

## 🧠 AI & Processing Modules

| File | Purpose |
|------|---------|
| `azure_openai_client.py` | Azure OpenAI integration |
| `header_mapper.py` | AI-powered field mapping |
| `chatbot_service.py` | Intelligent mapping suggestions |
| `file_parser.py` | File processing and data extraction |
| `pdftocsv.py` | PDF to CSV conversion |
| `data_validator.py` | Data validation and quality checks |

## 🗄️ Storage & Services

| File | Purpose |
|------|---------|
| `storage_service.py` | Unified storage interface |
| `s3_service.py` | AWS S3 integration |

## 🚀 Deployment Infrastructure

| File | Purpose |
|------|---------|
| `deploy-ec2.sh` | Automated EC2 deployment |
| `ec2-management.sh` | Instance management utilities |
| `user-data.sh` | EC2 initialization script |
| `setup-ec2-deployment.sh` | Interactive deployment setup |
| `deploy_to_ecr.sh` | Docker image build and push |

## 📚 Documentation

| File | Purpose |
|------|---------|
| `README.md` | Main project documentation |
| `README-EC2-DEPLOYMENT.md` | Comprehensive deployment guide |
| `ec2-console-setup-guide.md` | Manual console deployment |
| `ec2-deployment-guide.md` | Detailed deployment documentation |
| `DEPLOYMENT-SUCCESS.md` | Deployment success summary |

## ⚙️ Configuration

| File | Purpose |
|------|---------|
| `.env.template` | Environment configuration template |
| `.env` | Local environment variables (gitignored) |
| `.gitignore` | Git exclusion rules |

## 📁 Directories

| Directory | Purpose |
|-----------|---------|
| `static/` | Web assets (CSS, JS, images) |
| `templates/` | HTML templates |
| `config/` | Configuration modules |
| `uploads/` | File upload storage (runtime) |
| `templates_storage/` | Template storage (runtime) |
| `learned_preferences_storage/` | User preferences (runtime) |
| `tests/` | Test files |
| `docs/` | Additional documentation |

## 🧹 Removed Files

The following categories of files were removed during cleanup:

### App Runner Files (Deprecated)
- All `*apprunner*` files and configurations
- App Runner deployment scripts
- App Runner-specific Docker files

### Lambda Files (Deprecated)
- All Lambda deployment configurations
- SAM templates and configurations
- Lambda-specific handlers and configs

### Debug & Test Files
- Temporary debugging scripts
- Health check test files
- Minimal app versions for testing

### Temporary Documentation
- Feature-specific documentation files
- Quick setup guides (consolidated)
- Individual fix documentation

### Unused Configurations
- Alternative Docker configurations
- Backup and temporary files
- Development-only scripts

## 🎯 Current Focus

The repository now focuses exclusively on:

✅ **Production EC2 deployment** with Docker containers  
✅ **Automated deployment scripts** for easy setup  
✅ **Comprehensive documentation** for all deployment scenarios  
✅ **Clean, maintainable codebase** with clear structure  
✅ **AWS integration** (ECR, S3, IAM, CloudWatch)  
✅ **AI-powered features** with Azure OpenAI  

## 📊 Repository Stats

- **Total Files:** ~25 core files (excluding directories)
- **Deployment Scripts:** 5 automated scripts
- **Documentation Files:** 5 comprehensive guides
- **Core Application:** 10 Python modules
- **Configuration:** 3 essential config files

## 🚀 Quick Start

```bash
# Clone and deploy
git clone https://github.com/gauravpcu/vendor-statements.git
cd vendor-statements
./setup-ec2-deployment.sh
./deploy-ec2.sh
```

This clean structure makes the repository easy to understand, maintain, and deploy! 🎉
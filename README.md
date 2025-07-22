# MFA-scanner

Tool to check Microsoft 365 MFA configuration for security assessment.

## 🔍 Purpose

This script authenticates to Microsoft Graph using application credentials and checks whether MFA is enabled for each user in your tenant. It’s designed to support security assessment and misconfiguration detection tasks.

## ⚙️ Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Hasstatas/MFA-scanner.git
   cd MFA-scanner

## 🛠️ Configuration

Create a `.env` file in the root directory with the following:
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret
TENANT_ID=your-tenant-id

These credentials are used to authenticate with Microsoft Graph.

## ▶️ Usage

Run the scanner using:

```bash
python mfa_check_full.py



> ⚠️ Unable to proceed: waiting to see if admin can grant permission due to current access restrictions.

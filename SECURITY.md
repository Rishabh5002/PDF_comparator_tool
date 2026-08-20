# Security and Offline Processing

## Current design

The active comparison path is local-only:

`PDF -> PyMuPDF -> parser -> local matcher -> comparator -> local report`

No external AI API is required. PDF contents are not intentionally transmitted to a third-party service.

## Confidential documents

For enterprise use, the application should be deployed in an environment controlled by the organization. The current prototype does not claim enterprise certification or a complete security audit.

## Password-protected PDFs

Encrypted PDFs require the correct user password. The password is supplied to PyMuPDF for local authentication and is not sent to an external service. Incorrect or missing passwords stop processing. The application does not attempt to bypass encryption.

## Local processing controls

- PDF-only input validation
- 50 MB default size limit
- No cloud AI dependency in the active path
- No PDF-content logging
- Local report generation

## Future hardening

- OS/container sandboxing
- Stronger temporary-file lifecycle controls
- Access-control integration
- At-rest encryption where required by the deployment environment
- Dependency and vulnerability scanning
- Security/privacy review before production


## Input controls added in the offline core

Before PyMuPDF opens a user file, the application validates:

- the path exists and is a regular file;
- the extension is `.pdf`;
- the file is within the configured 50 MB default limit.

The core reads the source PDF directly and does not create a working copy or
temporary extraction file. Reports are written only to the explicit output
path requested by the caller.

## Offline verification boundary

The project includes an application-level `verify_offline_core()` check. It
states that the comparison path has no required network calls or cloud-AI
dependency. It is **not** a substitute for an OS/container firewall, because
Python cannot prove that arbitrary host processes are unable to access the
network.

For a real confidential-data deployment, enforce outbound network policy at
the operating-system/container/network layer as well.

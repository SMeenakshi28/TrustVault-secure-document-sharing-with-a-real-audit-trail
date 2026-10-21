\# TrustVault — Threat Model



\## 1. Purpose



TrustVault is a secure document-sharing platform designed to enforce role-based access control and maintain an audit trail of document-related activity.



\## 2. Assets to Protect



\- User credentials and authentication tokens

\- Document metadata and private document contents

\- Document-sharing permissions and expiry settings

\- Audit logs and their integrity

\- User roles and account status



\## 3. Threats and Mitigations



| Threat | Potential impact | Mitigation |

|---|---|---|

| Unauthorized document access | A user reads documents without permission. | Enforce ownership, viewer identity, and sharing permissions in backend routes. |

| Privilege escalation | A viewer performs owner or admin operations. | Enforce role checks on the backend instead of relying only on frontend navigation. |

| Invalid or unauthorized sharing | Documents are shared with unsuitable or unauthorized accounts. | Validate recipient accounts and sharing permissions before creating a share. |

| Expired or revoked access | A viewer continues accessing a document after permission expires or is revoked. | Check access validity when processing protected document requests. |

| Credential compromise | An attacker uses another user's account. | Hash passwords, verify credentials, and use signed authentication tokens. Protect secrets and use HTTPS in deployment. |

| Audit-log tampering | Activity records are altered or their integrity cannot be trusted. | Link audit events using hashes and provide audit-chain verification. Hash chaining alone does not prevent a privileged attacker from rewriting the entire chain. |

| Loss of application data | Users, documents, shares, and audit records disappear after a restart. | Current implementation uses in-memory state. Persistent database and storage integration with appropriate backups remain necessary. |

| Unauthorized file exposure | Private file contents are exposed through public or improperly protected storage. | Private object storage and backend-authorized file access are required before real file uploads and downloads are implemented. |



\## 4. Current Limitations



\- Application data is stored in memory and is not persistent.

\- Actual document file upload and download are not implemented.

\- The development JWT secret and development-only owner setup must not be used in production.

\- The audit chain is implemented in application memory and does not provide independent, tamper-resistant storage.

\- Production deployment requires secure secret management, HTTPS, persistent storage, and additional security testing.



\## 5. Security Testing



Backend tests cover authentication, role and permission checks, document-sharing behavior, and audit-chain verification. Tested cases include unauthorized access, invalid sharing requests, and denial of admin-only audit access to an owner.



Successful admin access and production security have not yet been fully verified.



\## 6. Scope



This document records the identified threats, current mitigations, and known gaps. It does not claim that TrustVault is production-ready or that all security risks have been eliminated.

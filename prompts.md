# TrustVault — AI-Assisted Development Prompts

## Day 1 — October 19, 2026

**Project:** TrustVault — Secure document sharing with a real audit trail

### Entry 1: Understanding the problem statement and user roles

**Prompt / request:**

Explain the TrustVault hackathon problem statement in simple terms. Describe the problem, the proposed solution, and the responsibilities of the admin, owner, and viewer.

**What AI produced:**

A simplified explanation of TrustVault as a secure document-sharing platform, where owners share documents with selected viewers and important document activities are recorded in an audit trail. It also explained the responsibilities of the three roles.

**What was wrong or incomplete:**

The distinction between the admin and document owner was initially unclear. I also needed clarification on whether each role required a separate application or separate screens.

**What I did instead:**

I clarified the role responsibilities and decided to use one application with separate dashboards for admin, owner, and viewer.

**Related commit:** No direct code commit — this entry documents problem-statement clarification and role planning.

### Entry 2: Selecting the technology stack and planning the project lifecycle

**Prompt / request:**

Help me choose a suitable technology stack for TrustVault and explain the project lifecycle from initialization through development, testing, deployment, and maintenance.

**What AI produced:**

A proposed architecture using React with Vite for the frontend, Python with FastAPI for the backend, Supabase PostgreSQL for the database, and private Supabase Storage for documents. It also outlined the major development stages.

**What was wrong or incomplete:**

The technology choices and lifecycle plan provided a starting point but did not constitute a working application. The integration, security, testing, deployment, and maintenance tasks still needed to be completed.

**What I did instead:**

I proceeded with the proposed architecture and planned to build the application in stages, starting with the frontend before integrating the backend and database.

**Related commit:** No direct code commit — this entry documents planning and technology selection.

### Entry 3: Exploring the UI design using Lovable

**Prompt / request:**

Provide a prompt for Lovable to generate a visual reference for the TrustVault interface, including the login screen and role-specific dashboards, so I could understand the design and build my own frontend.

**What AI produced:**

A prompt describing a secure document-sharing interface with role-based dashboards and document-management features.

**What was wrong or incomplete:**

The initial UI direction did not fully match the interface I wanted. I needed a clearer visual reference before continuing with the frontend implementation.

**What I did instead:**

I requested a Lovable prompt to explore the interface visually and use the generated design as a reference for building my own React frontend.

**Related commit:** No direct commit for the UI-reference prompt itself. Related frontend implementation

### Entry 4: Implementing the React frontend

**Prompt / request:**

Help me build the TrustVault frontend in React, starting with the login and sign-up screens and progressing toward role-specific dashboards. Explain the code and provide the relevant file paths.

**What AI produced:**

Frontend implementation guidance for the login and sign-up interfaces, form fields, password visibility, role selection in the prototype, navigation between screens, and role-based dashboard layouts.

**What was wrong or incomplete:**

The frontend was still a work in progress. Some screens and interactions were developed, but the application was not yet fully connected to backend authentication, document storage, or permission enforcement.

**What I did instead:**

I continued developing the frontend in stages and used the interface as a prototype, keeping the remaining integration and security work for subsequent development.

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/eab71cd

### Entry 5: Implementing form validation and identifying security limitations

**Prompt / request:**

Help me implement sign-up form validation, including password-strength requirements, and explain which security features must be handled by the backend.

**What AI produced:**

Password validation requirements covering minimum length, uppercase and lowercase letters, a number, and a special character. It also explained the difference between frontend validation and server-side security enforcement.

**What was wrong or incomplete:**

Frontend validation improves the user experience but can be bypassed. Allowing public users to assign themselves the Admin role would also be unsafe in the finished application.

**What I did instead:**

I treated frontend validation and role selection as prototype functionality and identified backend authentication, trusted role assignment, and server-side authorization as necessary follow-up tasks.

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/eab71cd


## Day 2 — October 20, 2026

**Project:** TrustVault — Secure document sharing with a real audit trail

### Entry 1: Building the backend authentication module and tests

**Prompt / request:**

Help me implement TrustVault backend authentication using Python. Create the required authentication files and corresponding tests, explain the code, and guide me through running the tests to verify the functionality.

**What AI produced:**

Python authentication code for user registration and login, role handling, password verification, and JWT-based authentication, along with test code for authentication behavior.

**What was wrong or incomplete:**

The implementation used in-memory user storage, so accounts were not persistent across server restarts. The development setup also used temporary credentials and a development JWT secret that would need to be secured before deployment.

**What I did instead:**

I implemented the authentication module and its corresponding tests, then proceeded with the backend integration after checking the authentication behavior.

**Concrete test results:**
- Owner login was tested using `owner@test.com`.
- Viewer registration and login were tested using `viewer@test.com`.
- These accounts were temporary and stored in memory; they would need to be recreated after a server restart.

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/23d6f89

### Entry 2: Implementing document management and permission handling

**Prompt / request:**

Help me implement the document-management and permission modules. Owners should be able to manage their documents, share them with eligible viewers, control permissions, and revoke access. Provide the code and tests.

**What AI produced:**

Python modules for document metadata management and sharing permissions, including ownership checks, viewer access, read/download flags, and expiration validation.

**What was wrong or incomplete:**

The document module handled metadata rather than actual file uploads. Recipient validation also needed to ensure that the selected recipient was a registered, active viewer.

**What I did instead:**

I implemented the document and permission modules and added recipient validation to reject ineligible recipients.

**Concrete test results:**
- Owner document creation and listing were tested successfully.
- A viewer could access documents shared with them.
- Revoking a share removed the viewer's access.
- A request with both `can_view` and `can_download` set to `false` returned **HTTP 400 Bad Request**.
- Sharing with an invalid or ineligible recipient returned **HTTP 400 Bad Request**, with the message: `Recipient must be an active viewer account.`

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/73f4d17

### Entry 3: Implementing the audit-trail module

**Prompt / request:**

Help me implement an audit-trail module that records important actions and provides a way to verify the integrity of the audit history.

**What AI produced:**

An audit module that records events, maintains previous-hash references, calculates event hashes, restricts audit-log viewing to administrators, and verifies the audit chain.

**What was wrong or incomplete:**

Audit events were stored in memory and would be lost after a server restart. Hash-chain verification was a useful integrity check, but it did not yet provide persistent, independently protected audit storage.

**What I did instead:**

I implemented the audit module and used a temporary development endpoint to check audit-chain validity.

**Concrete test results:**
- The audit-chain verification endpoint was tested during development. The previously recorded test status was valid (`{"valid": true}`), although the exact test output was not preserved in the conversation.
- The audit-log endpoint was tested with an owner account and correctly denied access with **HTTP 403 Forbidden** and the message: `Only admins can view the audit logs.`
- Successful access by an administrator was not yet confirmed.

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/c8f89cf

### Entry 4: Connecting the backend modules through FastAPI

**Prompt / request:**

Help me connect the authentication, document-management, permission, and audit modules through FastAPI. Create the API routes and explain how to test the endpoints using Swagger.

**What AI produced:**

FastAPI routes for registration, login, current-user information, document creation and listing, document deletion, sharing, viewing shared documents, revoking access, and administrator-only audit-log access.

**What was wrong or incomplete:**

Connecting the modules did not automatically guarantee that every operation was properly protected. Each endpoint needed to enforce authentication, role restrictions, and document-level permissions.

**What I did instead:**

I connected the modules through the FastAPI routes and tested the API through Swagger at `http://127.0.0.1:8000/docs`.

**Concrete test results:**
- The FastAPI server started successfully for development testing.
- Owner-only document operations were tested using an authenticated owner.
- An owner attempting to access the administrator audit-log endpoint received **HTTP 403 Forbidden**.
- Viewer access to shared documents and access revocation were tested as part of the API workflow.

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/5e2f948

### Entry 5: Testing role-based access control and identifying remaining gaps

**Prompt / request:**

Help me test TrustVault using different user roles. Verify owner and viewer behavior, invalid sharing requests, unauthorized access, administrator audit access, and audit-chain verification.

**What AI produced:**

A testing workflow covering authentication, document creation, sharing, viewing shared documents, revocation, invalid permission combinations, invalid recipients, administrator-only audit access, and audit-chain verification.

**What was wrong or incomplete:**

The backend still relied on in-memory storage. Actual file upload/download, persistent audit storage, and a confirmed successful administrator audit-log test remained incomplete or unverified.

**What I did instead:**

I exercised the API with owner and viewer accounts, checked expected success and failure responses, corrected recipient validation, and tested the audit endpoints. I recorded the remaining limitations instead of treating the backend as production-ready.

**Concrete test results:**

| Test | Observed result |
|---|---|
| Owner login | Tested successfully |
| Viewer registration/login | Tested successfully |
| Owner creates document metadata | Tested successfully |
| Viewer accesses a shared document | Tested successfully |
| Owner revokes viewer access | Tested; access was revoked |
| Invalid permission combination | HTTP 400 |
| Invalid/ineligible share recipient | HTTP 400 |
| Owner accesses admin audit logs | HTTP 403 |
| Audit-chain verification | Previously reported valid |
| Successful admin audit-log access | Not yet confirmed |
| Actual file upload/download | Not implemented yet |
| Data persistence after restart | Not supported by current in-memory implementation |

**Related commits:**

- Authentication and role security: https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/23d6f89
- Document permissions and sharing: https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/73f4d17
- Audit trail and integrity verification: https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/c8f89cf
- FastAPI integration: https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/5e2f948

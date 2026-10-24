# TrustVault: Threats and protections

## Why this document exists

TrustVault is a React frontend with a FastAPI backend, PostgreSQL metadata, Supabase file storage, and a hash-linked audit log. This document describes what the checked-in code does, what the tests cover, and what still needs protection. A screen or button is not proof that a backend permission check exists.

The main rule is: **a person must not get a document or do an action unless the backend confirms that person's permission.** The backend, not a role or document ID supplied by the browser, must make that decision.

The review is based on the repository code and tests, not on a live deployment. In particular, the actual production database, Supabase bucket policy, HTTPS setup, secret settings, and backup arrangements cannot be confirmed from this repository.

## Most important risks

1. **Uploaded files can contain active web content.** The upload accepts the browser-supplied content type, and the view endpoint serves it inline. The frontend now previews files inside a sandboxed frame that blocks script execution; browser-level testing is still needed.
2. **Email addresses are not verified.** A person can register an address they do not own. Since Owners share to an account by email, an attacker who claims an address first could receive a document intended for that address.
3. **There is no request rate limit in the application.** Repeated login, upload, or other requests could consume service resources or enable password guessing.
4. **A stolen login token can be reused until it expires.** Tokens last 30 minutes and are checked against current account status, but individual tokens are not revoked at logout.
5. **The audit hash chain is not independent proof.** It can detect ordinary edits, but a person who can rewrite the database can also recompute the unkeyed hashes.

Also verify that deployment secrets are protected and the Supabase bucket is private. The code uses a server-side service key, but repository code cannot prove the deployed bucket's access policy.

## Current test evidence

I ran the backend test suite from `backend` with `python -m pytest .\tests -q`: **70 passed, 1 skipped**. The suite uses an isolated in-memory SQLite database; it does not test the deployed PostgreSQL database or real Supabase storage. Several route tests replace storage with a test double. A passing suite is useful evidence for the cases it actually checks, not proof that every threat is blocked.

Relevant existing test names are listed with the threats below. Tests that are recommendations, not existing tests, are labeled as such.

## Threats

### 1. Changing a document ID to reach another person's file

**Threat:** A Viewer changes the document ID in a URL or directly calls the API for someone else's file.

**Example:** A Viewer replaces their shared document ID with an ID copied from another screen.

**Possible damage:** Private file contents or metadata could be exposed.

**How to prevent it:** Keep checking the signed-in user's current database account and active share on every request. The backend currently restricts shared document access to a matching active share, and Owner access is scoped to the Owner's own ID. Keep the storage request behind that check.

**How to test it:** Call the file and download API directly as a Viewer with no share and as a different Viewer who has a share to another file. Require a denial, no private response body, and no storage fetch. Also test the permitted recipient succeeds once.

**Status:** Implemented and verified. Existing coverage includes `test_viewer_list_is_scoped_and_other_viewer_cannot_fetch_file`, `test_unauthorized_document_download_is_denied_without_server_error`, and `test_shared_recipient_download_is_single_use` in `backend/tests/test_routes.py`.

### 2. Changing a role in the browser or forging an Admin role

**Threat:** A user changes a frontend role value, request field, or token role claim to try to become an Owner or Admin.

**Example:** A Viewer edits browser state to say `admin`, then calls `/admin/users`.

**Possible damage:** The user could manage accounts, change roles, or view data reserved for an Admin.

**How to prevent it:** Treat the database role as the authority. The backend reloads the user from the database for each token request; protected routes check that server-side role. Signup always creates a Viewer regardless of a client-supplied role. Keep role changes limited to an active Admin.

**How to test it:** Call admin and owner endpoints directly with a Viewer token and expect denial. Submit an Admin role during signup and in profile changes. Also create a token with a misleading role claim and prove the API still uses the database role. The last forged-claim case is a recommended test.

**Status:** Partially implemented. Backend checks and existing tests `test_signup_ignores_client_supplied_role`, `test_user_cannot_change_own_role_through_api`, and `test_profile_update_cannot_change_role` exist; there is no explicit test for a forged token role claim.

### 3. An Owner editing, deleting, or sharing another Owner's document

**Threat:** An Owner supplies another Owner's document ID to a management endpoint.

**Example:** Owner A sends a delete or share request naming Owner B's document.

**Possible damage:** Another person's document could be deleted, altered, or shared without consent.

**How to prevent it:** Include the authenticated Owner ID in database lookups and require the document to belong to that Owner. The document delete and share operations use this ownership condition. Do not trust an owner ID submitted by the browser.

**How to test it:** Call delete and share APIs with the other Owner's document ID. Confirm denial, document/file still exists, no share is created, and no private file content is returned. The cross-owner delete case should be explicitly covered.

**Status:** Partially implemented. The ownership check is in the code and `test_owner_cannot_share_another_owners_document` checks sharing; an API-level cross-owner delete/no-data-change test is missing.

### 4. A Viewer tries to share a document or grant extra permissions

**Threat:** A Viewer calls the sharing API directly or adds fields such as `can_download: true` or `can_view: true`.

**Example:** A Viewer skips the hidden Share button and sends a POST request to `/documents/{id}/share`.

**Possible damage:** A Viewer could give themselves or another person access the Owner did not grant.

**How to prevent it:** Require Owner role and ownership in the backend sharing route. The server sets `can_view` itself and only accepts the Owner's download choice; do not trust permission values from a Viewer.

**How to test it:** Make direct API calls as a Viewer to create and revoke shares, with extra permission fields, and require denial plus no database changes. Then confirm an Owner can create a share with only the selected permissions.

**Status:** Partially implemented. The route requires Owner role and the sharing logic sets view permission itself. A direct Viewer-to-share API test is not present.

### 5. Access after a share is revoked or expires

**Threat:** A recipient tries the same API request after the Owner revokes the share or its expiry time passes.

**Example:** A Viewer saves the document ID and requests the file again after revocation.

**Possible damage:** The recipient could keep getting new copies after access ends.

**How to prevent it:** Recheck revoked and expiry values when the file is requested and when the one-time access is consumed. The current code also hides revoked shares from the Viewer list.

**How to test it:** Create a share, revoke or expire it, and call both the file and download endpoints directly. Confirm denial, no contents returned, no second use, and no unauthorized storage response.

**Status:** Implemented and verified. Existing tests include `test_revoked_permission_is_rejected`, `test_expired_permission_is_rejected`, `test_revoked_share_disappears_from_viewer_list`, and `test_expired_or_revoked_share_cannot_be_downloaded`.

### 6. Accessing a private file without signing in

**Threat:** Someone calls document, share, or admin APIs without an access token.

**Example:** A person opens a guessed `/documents/{id}/file` address in a private browser window.

**Possible damage:** Anyone could read private files or metadata.

**How to prevent it:** Keep authentication required for protected routes and authorize the user after authentication. A storage object should not be public merely because its path is hard to guess.

**How to test it:** Call each protected file, list, share, and admin API with no token and with a malformed token. Expect an authentication error and no private response body or storage call.

**Status:** Partially implemented. Protected routes use HTTP Bearer authentication, and some no-token route cases are tested, but an unauthenticated document file/download test is not explicit.

### 7. Reusing a stolen or old login session

**Threat:** Someone who steals a token reuses it, or a user assumes logout immediately invalidates a copied token.

**Example:** A token copied before logout is replayed before its 30-minute expiry.

**Possible damage:** The attacker could act as that user until token expiry or account deactivation.

**How to prevent it:** Tokens are signed, expire after 30 minutes, and each API request checks that the account still exists and is active. However, the token ID (`jti`) is not tracked for individual revocation; frontend logout only clears the in-memory token. Consider short token lifetimes or a server-side revocation mechanism for sensitive deployments.

**How to test it:** Confirm expired or modified tokens are rejected. Log out, reuse the same token directly, and document that it remains valid until expiry unless revoked by deactivation. Confirm a deactivated account's existing token fails.

**Status:** Partially implemented. Expiry and current account status are checked. Existing coverage includes `test_valid_token_returns_user` and `test_existing_token_is_rejected_after_deactivation`; there is no individual logout/token-replay test.

### 8. Opening a direct file-storage URL

**Threat:** Someone bypasses TrustVault and tries to fetch an object directly from Supabase Storage.

**Example:** A Viewer discovers or guesses a storage path and requests it without a TrustVault token.

**Possible damage:** A public bucket or exposed storage key could reveal all stored files.

**How to prevent it:** The backend retrieves objects using a server-side service key and does not return that key or a signed storage URL. The README says the bucket must be private. The actual deployed bucket policy and key configuration must be checked separately.

**How to test it:** In a non-production Supabase project, request a test object's storage URL without credentials and require denial. Also inspect bucket policy and confirm no service-role key is present in frontend bundles, tracked files, or deployment logs.

**Status:** Partially implemented. Backend-mediated storage access is present; private bucket configuration is a deployment requirement and has not been verified here. There is no automated storage-policy test.

### 9. Uploading a huge file or lying about its file type

**Threat:** An Owner sends a large upload or labels harmful content as a safe type.

**Example:** A small HTML file is uploaded with `text/html`, or an oversized request is sent repeatedly.

**Possible damage:** Storage or memory may be exhausted. Active content may run when a recipient previews the file.

**How to prevent it:** The backend rejects empty files and files over 20 MiB. It reads at most one byte over the limit before rejecting. But the MIME type comes from the upload request and is not verified against the file's contents, and there is no request rate limit. Add server-side type detection/allowlisting and enforce request limits at the application and hosting layers.

**How to test it:** Upload a file just under and just over 20 MiB, an empty file, and a file whose contents do not match its declared type. Confirm rejected files are not stored and database metadata is unchanged. Add a test for repeated concurrent uploads.

**Status:** Partially implemented. A 20 MiB size check exists, and `test_owner_upload_still_persists_document_metadata` covers a successful upload with mocked storage. Content type validation, rate controls, and oversized/type-mismatch upload tests are missing.

### 10. Putting harmful code in a document or its name

**Threat:** An Owner uploads a document containing script or uses a name intended to run code in a browser.

**Example:** A Viewer opens a shared HTML file in TrustVault's preview tab.

**Possible damage:** Script could run in the application site and act as the logged-in user or expose data shown in that browser.

**How to prevent it:** The file view API returns the stored content type inline, so `nosniff` alone does not make HTML safe. Both Viewer and Owner previews now put the blob in an iframe with an empty `sandbox` attribute, which blocks scripts and gives the content an isolated origin. Keep the sandbox restrictive and consider safe file-type allowlisting or a separate untrusted-content origin for stronger isolation. React renders names as text in the inspected UI; keep avoiding raw HTML insertion.

**How to test it:** In a safe test environment, upload a harmless HTML file containing a visible script marker and share it. Confirm opening it cannot execute in the TrustVault origin and that downloaded bytes remain unchanged. Also test a filename containing HTML-like characters in list and share views.

**Status:** Partially implemented. Both frontend preview paths use a restrictive sandbox, but this new browser behavior has not yet been tested in an actual browser. The backend still accepts the client-supplied content type, and there is no upload/preview safety test.

### 11. Creating fake activity or changing audit records

**Threat:** A user tries to create false activity or someone with database write access changes or deletes audit rows.

**Example:** A database operator edits an event and recomputes the following hashes.

**Possible damage:** The history could no longer be trusted to prove who did what.

**How to prevent it:** Normal application users have no audit-write endpoint; events are created by backend code. The hash chain detects changes that do not also update the chain. It is not protected against someone who can rewrite the database because the hashes are unkeyed and checked against the same database. For stronger evidence, send signed checkpoints to separately controlled append-only storage.

**How to test it:** Confirm an ordinary Viewer cannot call an API to create, edit, or delete events. Change an event in a test database without updating its hash and expect verification to fail. The current tampering test checks this basic case, not a full rewrite by a database administrator.

**Status:** Partially implemented. `test_tampering_is_detected` verifies basic tampering detection; external tamper-resistant storage and a privileged-rewrite test are absent.

### 12. Seeing private document names in lists or search

**Threat:** A user tries to discover names or details for documents not shared with them.

**Example:** A Viewer searches for a guessed private filename or calls the list endpoint for another user.

**Possible damage:** Even without file contents, filenames and document details may be sensitive.

**How to prevent it:** The Viewer list is scoped to shares for the authenticated user's ID. Owner document lists are scoped to the Owner ID. The inspected frontend search filters the documents already returned; it is not a global database search.

**How to test it:** Give two Viewers different shares and include a distinctive private filename in one. Call the list/search API as the other Viewer and confirm neither that name nor metadata appears.

**Status:** Implemented and verified for the shared list. `test_viewer_list_is_scoped_and_other_viewer_cannot_fetch_file` checks list scoping; there is no separate search-specific test because no global search API was found.

### 13. A disabled account continuing to access files

**Threat:** An account is deactivated but keeps using a token or an old share.

**Example:** An Admin disables a Viewer, who then replays a token saved earlier.

**Possible damage:** A removed user could continue accessing files or other protected functions.

**How to prevent it:** The backend reloads the account and checks `active` for every token request. Admin deactivation also revokes the user's active shares.

**How to test it:** Deactivate an account with an active token and share. Call the file API and other protected APIs with the old token, then check the share is revoked and no file content is returned.

**Status:** Implemented and verified. Existing tests include `test_existing_token_is_rejected_after_deactivation` and `test_deactivation_revokes_shares_but_preserves_records`.

### 14. Finding passwords or secret keys in source or frontend files

**Threat:** Someone obtains a database password, JWT signing key, or Supabase service key from committed files or frontend code.

**Example:** A deployment accidentally bundles a backend service key into the React application.

**Possible damage:** An attacker could impersonate users, read or alter database rows, or bypass storage rules.

**How to prevent it:** Backend configuration reads secrets from environment variables; `.env` is ignored and `.env.example` is a template. The development-owner option creates a known-password account if explicitly enabled; the README warns to keep it disabled. Never put service keys in `frontend` variables or commit real `.env` files. Use a secret scanner and rotate any exposed key.

**How to test it:** Scan tracked files and built frontend assets for real credentials, verify the test-owner flag is false in deployment, and confirm the backend refuses to start without a sufficiently long JWT secret. This review did not inspect deployment secret values.

**Status:** Partially implemented. Configuration and ignore-file protections exist, but actual deployment values and automated secret scanning are unverified.

### 15. Sending too many requests

**Threat:** Someone repeatedly requests login attempts, uploads, or protected endpoints to consume service resources.

**Example:** A script repeatedly submits wrong passwords or starts many 20 MiB uploads.

**Possible damage:** Legitimate users could be slowed down or locked out; storage, memory, or hosting costs could rise.

**How to prevent it:** No application-level rate limiter was found. Add limits at the API or hosting layer for login, signup, upload, and expensive routes, plus monitoring and sensible request/body limits.

**How to test it:** In a non-production environment, send requests above the configured threshold and confirm they are limited without affecting normal users. Add automated tests for the expected limit and reset window after implementing one.

**Status:** Not implemented.

### 16. Reusing an old download or preview link after revocation

**Threat:** A recipient reuses an old API request or a file that was already delivered after access is revoked.

**Example:** The Owner revokes a share after a Viewer has opened or downloaded the file.

**Possible damage:** A saved copy or already-open preview can remain available. A copy already downloaded to another device cannot be remotely erased.

**How to prevent it:** TrustVault does not return a public storage URL; new file requests go through backend authorization. Revocation blocks new requests. Once file bytes have been delivered to a recipient, however, the server cannot claw them back. Avoid promising remote deletion.

**How to test it:** Revoke a share and repeat the authenticated API request; expect denial and no new content. Separately verify and explain that an already downloaded copy still opens offline.

**Status:** Partially implemented. New API access is checked and revocation tests exist; deletion of already delivered copies is not possible by design.

### 17. Changing request fields to access another user's data

**Threat:** A user changes IDs or fields in a request body to name another user or owner.

**Example:** A Viewer changes a profile update body or share request to include another user's ID.

**Possible damage:** Data could be read or changed under the wrong account.

**How to prevent it:** Derive the acting user's ID and role from the authenticated account, and validate every target against ownership or explicit Admin authority. Do not accept authority from client-supplied fields.

**How to test it:** Change document, share, target-user, and profile IDs/fields in direct API requests. For each denied request, check that private response content is absent and the database rows remain unchanged.

**Status:** Partially implemented. Several routes derive identity from the token and check ownership/role, and role-manipulation tests exist. A complete per-endpoint altered-ID/no-change test set is missing.

### 18. Misuse or compromise of an Admin account

**Threat:** An Admin account is abused to manage users or inspect more activity than intended.

**Example:** A compromised Admin disables a user, promotes another account, or reads global audit records.

**Possible damage:** User access and account roles could be changed, and global audit details are visible. The document endpoints do not grant Admins automatic access to document contents.

**How to prevent it:** Keep Admin accounts limited to trusted operators. The code checks active Admin role for management routes, logs role and account changes, prevents self-role change, and protects the last active Admin. Consider stronger sign-in protection and regular review of Admin activity.

**How to test it:** Confirm an Owner and Viewer cannot call Admin routes; confirm an active Admin can perform only intended management actions; confirm a disabled Admin and forged Admin request are denied. Existing tests cover several role and account-management cases, but there is no full test that Admin cannot fetch arbitrary document content.

**Status:** Partially implemented. Admin routes have backend role checks, and tests exist for management restrictions. Admin authentication hardening and complete document-boundary tests are missing.

### 19. Errors, temporary files, backups, or logs exposing information

**Threat:** Sensitive file contents, paths, credentials, or database details appear in an error, temporary file, log, or backup.

**Example:** A storage failure prints connection details, or an unprotected database backup is copied.

**Possible damage:** An attacker could learn deployment details or obtain data without using the application.

**How to prevent it:** Storage failures generally return generic API messages, and upload contents are handled in memory rather than written to an application temp file. Some storage failures are printed to backend logs. No backup or log-retention configuration is included in this repository; secure and access-limit operational logs and encrypt and test backups.

**How to test it:** Cause controlled database and storage failures in a test deployment; inspect API responses and logs for credentials, tokens, file contents, or sensitive URLs. Confirm backups are access-restricted and can be restored.

**Status:** Partially implemented. Some generic error responses and in-memory upload handling exist; log controls, backup protection, and recovery tests are not verified.

### 20. A download races with permission revocation

**Threat:** A file request and a revoke/deactivate request happen at nearly the same time.

**Example:** A Viewer starts fetching a file as the Owner revokes their share.

**Possible damage:** An in-flight operation might complete around the same time as revocation. A response already delivered cannot be recalled.

**How to prevent it:** TrustVault checks authorization before fetching and checks/consumes one-time access again in a database transaction before returning the response. The access-consumption step uses row locking and a conditional update. This narrows the race, but cannot recall bytes after authorization has been consumed and a response is already being sent. Define the rule as "revocation blocks later requests," not "revocation erases a request already in progress."

**How to test it:** Use a concurrency test that pauses a mocked storage fetch, revokes the share, then lets the request continue. Confirm the request is denied if revocation wins before access is consumed. Also test the reverse ordering and document that an already-authorized/in-flight response can finish. `test_concurrent_requests_grant_only_one_successful_access` tests one-time concurrent access, not revocation racing a real storage response.

**Status:** Partially implemented. Access is rechecked and one-time consumption is atomic; a revoke-versus-download integration test is missing.

### 21. Claiming another person's email before they register

**Threat:** A person signs up using an email address they do not control.

**Example:** An attacker registers a target's email first; an Owner later shares a document to that email, which TrustVault resolves to the attacker's account.

**Possible damage:** A document could be delivered to an unintended account.

**How to prevent it:** Verify control of an email address before allowing the account to receive shares. The current signup flow creates active accounts without email verification, and shares select recipients by registered email.

**How to test it:** Register an unverified address and attempt to share to it. After implementing verification, confirm it cannot receive/access shares until verification is complete.

**Status:** Not implemented. No email verification flow or verified-email state was found.

### 22. SQL injection through IDs or search values

**Threat:** Someone puts database commands into an ID or other request value.

**Example:** A malformed document ID is sent to a route to try to change the database query.

**Possible damage:** A successful database injection could expose or alter many records.

**How to prevent it:** The inspected data access uses SQLAlchemy query expressions and bound values rather than building SQL from user strings. Continue using parameterized queries for all database operations; do not concatenate request values into SQL.

**How to test it:** Send malformed IDs and search values through API routes and confirm they are treated as ordinary values or rejected, do not return other records, and do not alter data. Add this as a regression test if raw SQL is introduced.

**Status:** Implemented but not tested. The inspected database queries use SQLAlchemy expressions; no SQL-injection-specific test was found.

## Make authorization tests meaningful

The hackathon instruction means this: **a test must fail if someone removes the permission check it claims to test.** If a test still passes after the check is removed, the test was not actually protecting that rule.

For each important rule, test the backend/API directly rather than checking whether the frontend hides a button. Include both:

- A permitted person can complete the allowed action.
- An unauthorized person is rejected, receives no private file contents or sensitive metadata, and cannot change or delete data.

Use realistic database records and call the route with real test tokens. Where practical, assert that unauthorized requests never reach storage. If using mutation testing, do it only on a safe test branch and restore the authorization check; never weaken the application to demonstrate a test.

Useful existing coverage includes:

- `test_viewer_list_is_scoped_and_other_viewer_cannot_fetch_file`
- `test_unauthorized_document_download_is_denied_without_server_error`
- `test_owner_cannot_share_another_owners_document`
- `test_expired_or_revoked_share_cannot_be_downloaded`
- `test_shared_recipient_download_is_single_use`
- `test_existing_token_is_rejected_after_deactivation`
- `test_signup_ignores_client_supplied_role`
- `test_tampering_is_detected`

Important gaps include unauthenticated document-file tests, Viewer direct share attempts, cross-Owner delete attempts with unchanged-data assertions, forged token-role tests, HTML upload/preview safety, actual upload limits/type validation, storage policy checks, and revocation-versus-download race tests.

## Limitations and accepted risks

- A Viewer who can see a document can take a screenshot, copy text, or keep a delivered copy.
- Revoking a share blocks later backend requests; it cannot erase a file already downloaded or reliably close content already delivered to a browser.
- The one-time share logic limits successful delivery, but is not a digital-rights system that can prevent copying after delivery.
- A database administrator who can rewrite ordinary audit rows can recompute this unkeyed hash chain. Independent append-only storage is needed for stronger evidence.
- The backend expects PostgreSQL and Supabase Storage configuration, but tests use SQLite and mocked storage. Production access rules need separate checks.
- The code and README require a private Supabase bucket and secret environment variables; this repository review did not verify a live bucket policy, production secrets, HTTPS, backups, or deployment rate limits.
- No request rate limiter was found. This is a real gap, not a claim that an attack has happened.

TrustVault has useful authorization and audit protections, but these do not make the application impossible to hack or prove that a production deployment is secure.

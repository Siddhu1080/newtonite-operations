# Engineering Decisions — Newtonite Operations

## 1. Technology Stack

**Decision:** Use FastAPI, SQLAlchemy, MySQL, and React.

**Reasoning:** FastAPI provides a straightforward way to build REST APIs and validate requests. SQLAlchemy manages database operations and relationships, while MySQL provides persistent relational storage. React is used for the frontend.

**Trade-off:** This stack is familiar and maintainable, but it still requires careful database transaction handling, validation, and deployment configuration.

## 2. Team-Based Authorization

**Decision:** Associate users with teams through a `TeamMember` table and assign roles such as `admin` and `member`.

**Reasoning:** Users should access only work belonging to teams they are members of. Team creators are assigned the admin role, and only admins can add team members.

**Trade-off:** Membership checks add database queries, but they enforce access rules on the backend instead of relying on frontend controls.

## 3. Optimistic Concurrency Control

**Decision:** Add a version number to each work item and require clients to provide the version they are updating.

**Reasoning:** Two users might edit the same work item at approximately the same time. The update succeeds only if the stored version matches the submitted version. Successful updates increment the version, while stale updates receive HTTP 409 Conflict.

**Trade-off:** Clients must handle conflicts and fetch the latest version before retrying. This helps prevent one user's stale update from silently overwriting another user's changes.

## 4. Idempotent Work-Item Creation

**Decision:** Require an `Idempotency-Key` when creating a work item and store the key, request hash, and resulting work-item ID in the database.

**Reasoning:** A client may retry a request because of a timeout or an uncertain response. Reusing the same key and request body returns the original work item instead of creating another one. Reusing the key with a different request body results in HTTP 409 Conflict.

The idempotency record, work item, and creation activity are committed in the same database transaction.

**Trade-off:** This requires additional database storage and transaction logic, but reduces accidental duplicate operations.

## 5. Activity History and Automated Testing

**Decision:** Record important work-item actions in an `ActivityLog` table and test important system behaviors using automated tests.

**Reasoning:** Users need to understand what changed and who performed an action. Activity records capture work-item creation and updates. Automated tests cover important behaviors such as authorization, duplicate requests, invalid input, and stale updates.

**Trade-off:** Activity records increase database storage requirements. The test suite also requires a separate test database to avoid modifying application data.

## Known Limitations

- Notifications and background processing have not been implemented as part of the current backend scope.
- Authentication currently uses bearer JWTs with a 60-minute expiration; refresh-token functionality has not been implemented.
- The current authorization model supports team admins and members, but does not implement a more granular permission system.
- Automated tests cover important behaviors but do not establish complete test coverage or prove the absence of security vulnerabilities.
- Production readiness still requires deployment-specific configuration, operational monitoring, and further security and performance testing.


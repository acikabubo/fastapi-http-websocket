# Implement User Action Logging (Audit Logs)

## Overview
Implement comprehensive user action logging for security, compliance, and debugging purposes based on the documentation in `docs/guides/USER_ACTION_LOGGING.md`.

## Goals
- Track all user actions (HTTP and WebSocket) with detailed audit trail
- Meet compliance requirements (GDPR, audit retention)
- Enable security monitoring and incident investigation
- Provide debugging capabilities for user-reported issues

## Implementation Plan

### Phase 1: Database Model
- [ ] Create `UserAction` SQLModel in `app/models/user_action.py`
- [ ] Generate database migration (Alembic)
- [ ] Add indexes on frequently queried fields (user_id, timestamp, action_type)

### Phase 2: HTTP Request Logging
- [ ] Implement `AuditLogMiddleware` in `app/middlewares/audit_log.py`
- [ ] Add request payload sanitization (redact passwords, tokens)
- [ ] Register middleware in `app/__init__.py`
- [ ] Handle client IP from X-Forwarded-For header

### Phase 3: WebSocket Logging
- [ ] Extend `PackageRouter.handle_request()` with `_log_ws_action()`
- [ ] Log WebSocket request/response with req_id correlation
- [ ] Sanitize WebSocket payloads

### Phase 4: Configuration
- [ ] Add settings to `app/settings.py`:
  - `ENABLE_AUDIT_LOGGING: bool`
  - `AUDIT_LOG_RETENTION_DAYS: int`
  - `AUDIT_LOG_SAMPLE_RATE: float`
- [ ] Add feature flag support

### Phase 5: Performance Optimization
- [ ] Implement async background logging queue
- [ ] Add batch insert capability for high-volume scenarios
- [ ] Configure database partitioning by month (optional)

### Phase 6: Compliance & Cleanup
- [ ] Implement automated retention policy cleanup task
- [ ] Add GDPR data pseudonymization after retention period
- [ ] Create API endpoints for user data access requests

### Phase 7: Testing
- [ ] Unit tests for `AuditLogMiddleware`
- [ ] Integration tests for HTTP/WebSocket logging
- [ ] Test sanitization of sensitive fields
- [ ] Performance tests for high-volume scenarios

## Future Enhancements (Optional)
- [ ] Grafana Loki integration for operational monitoring
- [ ] Analytics dashboard endpoints
- [ ] Anomaly detection alerts
- [ ] Export to external SIEM systems

## Documentation
- ✅ Comprehensive guide added: `docs/guides/USER_ACTION_LOGGING.md`

## References
- [USER_ACTION_LOGGING.md](docs/guides/USER_ACTION_LOGGING.md)

## Labels
`enhancement`, `security`, `compliance`, `logging`

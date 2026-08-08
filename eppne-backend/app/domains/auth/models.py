# app/domains/auth/models.py
# RefreshToken now lives in app.domains.identity.models (Phase 1 of the
# auth->identity merge). Re-exported here so auth's own repository/service
# keep working unchanged until the auth domain is deleted (Phase 4).
from app.domains.identity.models import RefreshToken

__all__ = ["RefreshToken"]
"""API v1 routes"""
from fastapi import APIRouter

from app.api.v1 import auth, otp_auth, children, vaccinations, vaccines, hospitals, documents, abha, auth_tabs, beneficiaries, reminders, reports

api_router = APIRouter()

# Include all route modules
# OTP-based authentication (primary) - existing endpoints for backward compatibility
api_router.include_router(otp_auth.router, prefix="/auth", tags=["OTP Authentication"])

# Tab-based authentication (new) - Individual and Hospital login/registration
api_router.include_router(auth_tabs.router, prefix="/auth", tags=["Tab-based Authentication"])

# Legacy authentication (can be removed if not needed)
# api_router.include_router(auth.router, prefix="/auth/legacy", tags=["Legacy Authentication"])

api_router.include_router(children.router, prefix="/children", tags=["Child Profiles"])
api_router.include_router(beneficiaries.router, prefix="/beneficiaries", tags=["Beneficiaries"])
api_router.include_router(vaccinations.router, prefix="/vaccinations", tags=["Vaccinations"])
api_router.include_router(vaccines.router, prefix="/vaccines", tags=["Vaccine Master"])
api_router.include_router(hospitals.router, prefix="/hospitals", tags=["Hospitals"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(abha.router, prefix="/abha", tags=["ABHA Integration"])
api_router.include_router(reminders.router, prefix="/reminders", tags=["Vaccination Reminders"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])


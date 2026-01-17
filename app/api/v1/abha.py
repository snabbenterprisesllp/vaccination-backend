"""
ABHA Integration Endpoints

M1 SCOPE ONLY:
- ABHA creation/linking initiation
- OTP verification
- Demographic profile fetch

EXPLICITLY EXCLUDED:
- NO M2 consent manager endpoints
- NO M3 health data sync endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.abha import (
    ABHALinkRequest,
    ABHAConsentRequest,
    ABHALinkResponse,
    ABHAProfileResponse,
    ABHAInitiateRequest,
    ABHAInitiateResponse,
    ABHAVerifyRequest,
    ABHAVerifyResponse
)
from app.models.abha_link import ABHALink
from app.models.child_profile import ChildProfile
from app.models.user import User
from app.services.abha_service import ABHAService

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# ABHA M1 ENDPOINTS (M1 ONLY - NO M2/M3)
# ============================================================================

@router.post("/initiate", response_model=ABHAInitiateResponse, status_code=status.HTTP_200_OK)
async def initiate_abha(
    request: ABHAInitiateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate ABHA creation/linking (M1)
    
    This endpoint:
    - Initiates OTP-based ABHA authentication via ABDM Gateway
    - Supports both MOBILE_OTP and AADHAAR_OTP methods
    - Returns transaction_id for OTP verification
    
    M1 SCOPE: Only ABHA creation/linking, NO health data sync
    """
    try:
        # Validate person access
        if request.person_type == "parent":
            # Parent linking their own ABHA
            if request.person_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only link ABHA to your own account"
                )
        else:  # child
            # Verify child belongs to current user (parent)
            result = await db.execute(
                select(ChildProfile).where(
                    and_(
                        ChildProfile.id == request.person_id,
                        ChildProfile.parent_id == current_user.id
                    )
                )
            )
            child = result.scalar_one_or_none()
            if not child:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Child profile not found or access denied"
                )
        
        # Validate auth method requirements
        if request.auth_method == "MOBILE_OTP":
            if not request.mobile_number:
                # Use person's mobile number
                if request.person_type == "parent":
                    mobile = current_user.mobile_number
                else:
                    # For children, use parent's mobile
                    mobile = current_user.mobile_number
                request.mobile_number = mobile
        elif request.auth_method == "AADHAAR_OTP":
            if not request.aadhaar_number:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Aadhaar number required for AADHAAR_OTP method"
                )
        
        # Initiate ABHA auth via ABDM Gateway
        abha_service = ABHAService()
        
        # Check if ABHA is enabled
        if not abha_service.abha_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ABHA integration is not enabled. Please configure ABDM Gateway credentials. See docs/ABHA_CONFIGURATION.md"
            )
        
        result = await abha_service.initiate_abha_auth(
            auth_method=request.auth_method,
            mobile_number=request.mobile_number,
            aadhaar_number=request.aadhaar_number
        )
        
        # Log action for audit (never log Aadhaar)
        logger.info(
            f"ABHA initiation: user_id={current_user.id}, "
            f"person_type={request.person_type}, person_id={request.person_id}, "
            f"auth_method={request.auth_method}, txn_id={result['transaction_id'][:10]}..."
        )
        
        return ABHAInitiateResponse(
            transaction_id=result["transaction_id"],
            message="OTP sent successfully. Please verify to complete ABHA linking."
        )
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"ABHA initiation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate ABHA linking: {str(e)}"
        )


@router.post("/verify", response_model=ABHAVerifyResponse, status_code=status.HTTP_200_OK)
async def verify_abha(
    request: ABHAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify OTP and complete ABHA linking (M1)
    
    This endpoint:
    - Verifies OTP with ABDM Gateway
    - Fetches ABHA demographic profile
    - Links ABHA to person (parent or child)
    - Stores minimal ABHA data only
    
    M1 SCOPE: Only demographic profile, NO health records
    """
    try:
        # Verify person access
        if request.person_type == "parent":
            if request.person_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only link ABHA to your own account"
                )
            person = current_user
        else:  # child
            result = await db.execute(
                select(ChildProfile).where(
                    and_(
                        ChildProfile.id == request.person_id,
                        ChildProfile.parent_id == current_user.id
                    )
                )
            )
            person = result.scalar_one_or_none()
            if not person:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Child profile not found or access denied"
                )
        
        # Verify OTP and get ABHA details
        abha_service = ABHAService()
        abha_result = await abha_service.verify_otp_and_get_abha(
            transaction_id=request.transaction_id,
            otp=request.otp,
            auth_method=request.auth_method
        )
        
        # Mask ABHA number before storage (security)
        masked_abha = abha_service.mask_abha_number(abha_result["abha_number"])
        
        # Get demographic profile
        demographic = abha_result.get("demographic", {})
        
        # Link ABHA to person
        if request.person_type == "parent":
            person.abha_number = masked_abha
            person.abha_address = abha_result["abha_address"]
            person.abha_linked = True
            person.abha_linked_at = datetime.now()
        else:  # child
            person.abha_number = masked_abha
            person.abha_address = abha_result["abha_address"]
            person.abha_linked = True
            person.abha_linked_at = datetime.now()
            person.guardian_person_id = current_user.id  # Parent who linked
        
        await db.commit()
        await db.refresh(person)
        
        # Log action for audit
        logger.info(
            f"ABHA linked: user_id={current_user.id}, "
            f"person_type={request.person_type}, person_id={request.person_id}, "
            f"abha_number={masked_abha}, abha_address={abha_result['abha_address']}"
        )
        
        return ABHAVerifyResponse(
            success=True,
            abha_linked=True,
            abha_number=masked_abha,
            abha_address=abha_result["abha_address"],
            demographic=demographic,
            message="ABHA linked successfully"
        )
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"ABHA verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify ABHA: {str(e)}"
        )


# ============================================================================
# EXISTING ENDPOINTS (KEPT FOR BACKWARD COMPATIBILITY)
# ============================================================================

@router.post("/link", response_model=ABHALinkResponse, status_code=status.HTTP_201_CREATED)
async def link_abha(
    link_data: ABHALinkRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Link ABHA to child profile"""
    # Verify child belongs to user
    result = await db.execute(
        select(ChildProfile).where(
            and_(
                ChildProfile.id == link_data.child_id,
                ChildProfile.parent_id == current_user.id
            )
        )
    )
    child = result.scalar_one_or_none()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child profile not found"
        )
    
    # Check if already linked
    result = await db.execute(
        select(ABHALink).where(
            and_(
                ABHALink.child_id == link_data.child_id,
                ABHALink.abha_number == link_data.abha_number,
                ABHALink.is_active == True
            )
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ABHA already linked to this child"
        )
    
    # Create ABHA link
    # TODO: Integrate with actual ABHA API for verification
    
    abha_link = ABHALink(
        child_id=link_data.child_id,
        abha_number=link_data.abha_number,
        abha_address=link_data.abha_address,
        consent_given=link_data.consent_given,
        consent_date=datetime.now() if link_data.consent_given else None,
        consent_expiry=datetime.now() + timedelta(days=365) if link_data.consent_given else None,
        linked=True,
        linked_at=datetime.now()
    )
    
    # Update child profile
    child.abha_number = link_data.abha_number
    
    db.add(abha_link)
    await db.commit()
    await db.refresh(abha_link)
    
    return abha_link


@router.get("/child/{child_id}", response_model=ABHALinkResponse)
async def get_abha_link(
    child_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get ABHA link for a child"""
    result = await db.execute(
        select(ABHALink).where(
            and_(
                ABHALink.child_id == child_id,
                ABHALink.is_active == True
            )
        )
    )
    abha_link = result.scalar_one_or_none()
    
    if not abha_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No ABHA link found for this child"
        )
    
    return abha_link


@router.post("/child/{child_id}/consent", response_model=ABHALinkResponse)
async def update_consent(
    child_id: int,
    consent_data: ABHAConsentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update ABHA consent"""
    result = await db.execute(
        select(ABHALink).where(
            and_(
                ABHALink.child_id == child_id,
                ABHALink.is_active == True
            )
        )
    )
    abha_link = result.scalar_one_or_none()
    
    if not abha_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No ABHA link found for this child"
        )
    
    abha_link.consent_given = consent_data.consent_given
    if consent_data.consent_given:
        abha_link.consent_date = datetime.now()
        abha_link.consent_expiry = datetime.now() + timedelta(days=consent_data.consent_duration_days)
    else:
        abha_link.consent_expiry = None
    
    await db.commit()
    await db.refresh(abha_link)
    
    return abha_link


@router.get("/profile/{abha_number}", response_model=ABHAProfileResponse)
async def get_abha_profile(
    abha_number: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get ABHA profile (mock - requires actual ABHA API integration)"""
    # TODO: Integrate with actual ABHA API
    
    return ABHAProfileResponse(
        abha_number=abha_number,
        abha_address=f"{abha_number}@abdm",
        name="Mock User",
        date_of_birth="2020-01-01",
        gender="male",
        mobile=None,
        email=None,
        profile_photo=None
    )


@router.delete("/child/{child_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_abha(
    child_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Unlink ABHA from child profile"""
    result = await db.execute(
        select(ABHALink).where(
            and_(
                ABHALink.child_id == child_id,
                ABHALink.is_active == True
            )
        )
    )
    abha_link = result.scalar_one_or_none()
    
    if not abha_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No ABHA link found for this child"
        )
    
    # Soft delete
    abha_link.is_active = False
    abha_link.linked = False
    
    # Update child profile
    result = await db.execute(
        select(ChildProfile).where(ChildProfile.id == child_id)
    )
    child = result.scalar_one_or_none()
    if child:
        child.abha_number = None
    
    await db.commit()
    
    return None


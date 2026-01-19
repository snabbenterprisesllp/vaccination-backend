"""Immunization Report endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.beneficiary_service import BeneficiaryService
from app.services.vaccination_timeline_service import VaccinationTimelineService
from app.models.user import User
from app.utils.pdf_generator import generate_immunization_report_pdf

router = APIRouter()


@router.get("/beneficiaries/{beneficiary_id}/immunization-report")
async def get_immunization_report(
    beneficiary_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    format: str = Query("pdf", regex="^(pdf|json)$", description="Output format: pdf or json")
):
    """
    Generate immunization report for a beneficiary
    
    Returns a PDF report containing only administered (COMPLETED) vaccinations.
    This is suitable for official use, school admission, travel, etc.
    """
    service = BeneficiaryService(db)
    timeline_service = VaccinationTimelineService(db)
    
    # Verify beneficiary belongs to current user
    beneficiary = await service.get_beneficiary_by_id(beneficiary_id, current_user)
    if not beneficiary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beneficiary not found"
        )
    
    # Get vaccination timeline
    timeline_data = await timeline_service.get_child_timeline(
        beneficiary_id=beneficiary_id,
        user_id=current_user.id
    )
    
    # Filter only administered (COMPLETED) vaccinations
    administered_vaccines = [
        item for item in timeline_data.get("timeline", [])
        if item.get("status") == "COMPLETED"
    ]
    
    if format == "json":
        return {
            "beneficiary": {
                "id": beneficiary.id,
                "name": f"{beneficiary.first_name} {beneficiary.last_name}",
                "date_of_birth": beneficiary.date_of_birth.isoformat() if beneficiary.date_of_birth else None,
                "gender": beneficiary.gender,
            },
            "administered_vaccines": administered_vaccines,
            "total_count": len(administered_vaccines),
            "generated_at": timeline_data.get("generated_at")
        }
    
    # Generate PDF
    try:
        pdf_bytes = await generate_immunization_report_pdf(
            beneficiary=beneficiary,
            timeline_data=timeline_data,
            administered_vaccines=administered_vaccines
        )
        
        beneficiary_name = f"{beneficiary.first_name}_{beneficiary.last_name}".replace(" ", "_")
        filename = f"immunization_report_{beneficiary_name}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF report: {str(e)}"
        )


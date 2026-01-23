"""
Facility User mapping model

Maps users to facilities with role-based access.
Supports multi-facility assignments (user can belong to multiple facilities).
"""
from sqlalchemy import Column, Integer, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class FacilityRole(str, enum.Enum):
    """Facility user roles"""
    SUPER_ADMIN = "super_admin"      # Global admin - can manage all facilities
    FACILITY_ADMIN = "facility_admin"  # Facility administrator
    DOCTOR = "doctor"                # Doctor/Physician
    STAFF = "staff"                  # Support staff


class FacilityUser(BaseModel):
    """
    Facility User mapping - links users to facilities with roles
    
    This table enables:
    - One user can belong to multiple facilities with different roles
    - Role-based access control (SUPER_ADMIN, FACILITY_ADMIN, DOCTOR, STAFF)
    - Facility-specific permissions
    
    Note: SUPER_ADMIN users may have a facility_id=NULL to indicate global scope
    """
    __tablename__ = "facility_users"
    
    # User reference
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Facility reference (NULL for SUPER_ADMIN with global scope)
    facility_id = Column(Integer, ForeignKey("facilities.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Facility role
    facility_role = Column(SQLEnum(FacilityRole), nullable=False)
    
    # Active status for this facility assignment
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Assigned by (user_id who created this assignment)
    assigned_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="facility_assignments", foreign_keys=[user_id])
    facility = relationship("Facility", back_populates="facility_users")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])
    
    def __repr__(self):
        facility_info = f"facility_id={self.facility_id}" if self.facility_id else "global"
        return f"<FacilityUser user_id={self.user_id} {facility_info} role={self.facility_role.value}>"


"""
Hospital User mapping model

Maps users to hospitals with role-based access.
This table links users with login_type=HOSPITAL to hospitals and their roles.
"""
from sqlalchemy import Column, Integer, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class HospitalRole(str, enum.Enum):
    """Hospital user roles"""
    ADMIN = "admin"   # Hospital administrator
    DOCTOR = "doctor" # Doctor/Physician
    STAFF = "staff"   # Support staff


class HospitalUser(BaseModel):
    """
    Hospital User mapping - links users to hospitals with roles
    
    This table enables:
    - One user can belong to one hospital (or multiple if needed)
    - Role-based access control (ADMIN, DOCTOR, STAFF)
    - Hospital-specific permissions
    """
    __tablename__ = "hospital_users"
    
    # User reference
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Hospital reference
    hospital_id = Column(Integer, ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Hospital role (ADMIN, DOCTOR, STAFF)
    hospital_role = Column(SQLEnum(HospitalRole), nullable=False, default=HospitalRole.STAFF)
    
    # Active status for this hospital assignment
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="hospital_assignments")
    hospital = relationship("Hospital", back_populates="hospital_users")
    
    def __repr__(self):
        return f"<HospitalUser user_id={self.user_id} hospital_id={self.hospital_id} role={self.hospital_role.value}>"


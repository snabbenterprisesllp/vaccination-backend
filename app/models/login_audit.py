"""Login Audit model for tracking user logins"""
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class LoginAudit(Base):
    """Track all login attempts and sessions"""
    __tablename__ = "login_audits"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # User information
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    mobile_number = Column(String(15), nullable=False, index=True)
    
    # Session details
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    device_info = Column(String(500), nullable=True)
    
    # Login metadata
    login_method = Column(String(50), default="otp", nullable=False)  # otp, admin_override, etc.
    login_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Optional session tracking
    session_id = Column(String(255), nullable=True)
    logout_time = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="login_audits")
    
    def __repr__(self):
        return f"<LoginAudit user={self.mobile_number} at {self.login_time}>"



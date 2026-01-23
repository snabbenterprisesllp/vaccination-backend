"""
Tests for RBAC system
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User, LoginType
from app.models.facility import Facility
from app.models.facility_user import FacilityUser, FacilityRole
from app.services.token_service import TokenService


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
async def super_admin_user(db: AsyncSession):
    """Create a SUPER_ADMIN user"""
    user = User(
        mobile_number="+919999999999",
        full_name="Super Admin",
        login_type=LoginType.HOSPITAL,
        consent_given='Y'
    )
    db.add(user)
    await db.flush()
    
    facility_user = FacilityUser(
        user_id=user.id,
        facility_id=None,
        facility_role=FacilityRole.SUPER_ADMIN,
        is_active=True
    )
    db.add(facility_user)
    await db.commit()
    await db.refresh(user)
    
    return user


@pytest.fixture
async def facility_admin_user(db: AsyncSession, facility: Facility):
    """Create a FACILITY_ADMIN user"""
    user = User(
        mobile_number="+919888888888",
        full_name="Facility Admin",
        login_type=LoginType.HOSPITAL,
        consent_given='Y'
    )
    db.add(user)
    await db.flush()
    
    facility_user = FacilityUser(
        user_id=user.id,
        facility_id=facility.id,
        facility_role=FacilityRole.FACILITY_ADMIN,
        is_active=True
    )
    db.add(facility_user)
    await db.commit()
    await db.refresh(user)
    
    return user


@pytest.fixture
async def facility(db: AsyncSession):
    """Create a test facility"""
    facility = Facility(
        name="Test Hospital",
        facility_code="TEST001",
        facility_type="hospital",
        address="123 Test St",
        city="Test City",
        state="Test State",
        pincode="123456",
        country="India"
    )
    db.add(facility)
    await db.commit()
    await db.refresh(facility)
    
    return facility


class TestRBAC:
    """Test RBAC functionality"""
    
    def test_super_admin_can_create_facility(self, client, super_admin_user):
        """Test SUPER_ADMIN can create facility"""
        # Create token
        token = TokenService.create_access_token({
            "user_id": super_admin_user.id,
            "mobile_number": super_admin_user.mobile_number,
            "is_super_admin": True,
            "facility_ids": [],
            "facility_roles": {}
        })
        
        # Create facility
        response = client.post(
            "/api/v1/facilities",
            json={
                "name": "New Hospital",
                "facility_code": "NEW001",
                "facility_type": "hospital",
                "address": "456 New St",
                "city": "New City",
                "state": "New State",
                "pincode": "654321"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        assert response.json()["name"] == "New Hospital"
    
    def test_facility_admin_cannot_create_facility(self, client, facility_admin_user):
        """Test FACILITY_ADMIN cannot create facility"""
        token = TokenService.create_access_token({
            "user_id": facility_admin_user.id,
            "mobile_number": facility_admin_user.mobile_number,
            "is_super_admin": False,
            "facility_ids": [1],
            "facility_roles": {1: "facility_admin"}
        })
        
        response = client.post(
            "/api/v1/facilities",
            json={
                "name": "Unauthorized Hospital",
                "facility_code": "UNAUTH001",
                "facility_type": "hospital",
                "address": "789 Unauthorized St",
                "city": "Unauthorized City",
                "state": "Unauthorized State",
                "pincode": "999999"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403
    
    def test_facility_admin_can_manage_own_facility_users(self, client, facility_admin_user, facility):
        """Test FACILITY_ADMIN can manage users for their facility"""
        token = TokenService.create_access_token({
            "user_id": facility_admin_user.id,
            "mobile_number": facility_admin_user.mobile_number,
            "is_super_admin": False,
            "facility_ids": [facility.id],
            "facility_roles": {facility.id: "facility_admin"}
        })
        
        # Add user to facility
        response = client.post(
            f"/api/v1/facilities/{facility.id}/users",
            json={
                "mobile_number": "+919777777777",
                "full_name": "New Doctor",
                "role": "doctor"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
    
    def test_facility_admin_cannot_access_other_facility(self, client, facility_admin_user):
        """Test FACILITY_ADMIN cannot access other facilities"""
        token = TokenService.create_access_token({
            "user_id": facility_admin_user.id,
            "mobile_number": facility_admin_user.mobile_number,
            "is_super_admin": False,
            "facility_ids": [1],
            "facility_roles": {1: "facility_admin"}
        })
        
        # Try to access facility 999 (doesn't belong to user)
        response = client.get(
            "/api/v1/facilities/999/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403
    
    def test_super_admin_can_view_global_analytics(self, client, super_admin_user):
        """Test SUPER_ADMIN can view global analytics"""
        token = TokenService.create_access_token({
            "user_id": super_admin_user.id,
            "mobile_number": super_admin_user.mobile_number,
            "is_super_admin": True,
            "facility_ids": [],
            "facility_roles": {}
        })
        
        response = client.get(
            "/api/v1/analytics/global",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "total_facilities" in response.json()
    
    def test_facility_admin_cannot_view_global_analytics(self, client, facility_admin_user):
        """Test FACILITY_ADMIN cannot view global analytics"""
        token = TokenService.create_access_token({
            "user_id": facility_admin_user.id,
            "mobile_number": facility_admin_user.mobile_number,
            "is_super_admin": False,
            "facility_ids": [1],
            "facility_roles": {1: "facility_admin"}
        })
        
        response = client.get(
            "/api/v1/analytics/global",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403


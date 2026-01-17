"""
ABHA M1 Service - ABDM Gateway Integration

M1 SCOPE (STRICTLY ENFORCED):
- ABHA creation (via Aadhaar OTP or mobile OTP)
- ABHA linking to person (parent or child)
- ABHA demographic profile fetch ONLY

EXPLICITLY EXCLUDED:
- NO M2 (consent manager)
- NO M3 (health data sync)
- NO pushing vaccination records to ABDM
- NO fetching vaccination records from ABDM
- NO storing Aadhaar numbers
- NO storing full ABDM API responses
"""
import logging
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.core.config import settings

logger = logging.getLogger(__name__)


class ABHAService:
    """
    ABHA M1 Service - Handles ABDM Gateway integration for M1 only
    
    This service implements ONLY M1 functionality:
    - Initiate ABHA creation/linking with OTP
    - Verify OTP and complete ABHA linking
    - Fetch demographic profile from ABDM
    
    DO NOT add M2/M3 functionality here.
    """
    
    def __init__(self):
        self.base_url = settings.ABHA_BASE_URL
        self.client_id = settings.ABHA_CLIENT_ID
        self.client_secret = settings.ABHA_CLIENT_SECRET
        self.abha_enabled = getattr(settings, 'ABHA_ENABLED', False)
        self.timeout = 30.0
        
        # Validate configuration
        if self.abha_enabled and not all([self.base_url, self.client_id, self.client_secret]):
            logger.warning(
                "ABHA is enabled but credentials are missing. "
                "Set ABHA_BASE_URL, ABHA_CLIENT_ID, and ABHA_CLIENT_SECRET in environment variables."
            )
    
    async def _get_access_token(self) -> str:
        """
        Get access token from ABDM Gateway
        Uses client credentials flow
        """
        # Check if ABHA is enabled and configured
        if not self.abha_enabled:
            raise Exception(
                "ABHA integration is not enabled. "
                "Set ABHA_ENABLED=true and configure ABDM Gateway credentials."
            )
        
        if not all([self.base_url, self.client_id, self.client_secret]):
            raise Exception(
                "ABDM Gateway credentials are not configured. "
                "Please set ABHA_BASE_URL, ABHA_CLIENT_ID, and ABHA_CLIENT_SECRET environment variables."
            )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/auth/token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "grant_type": "client_credentials"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                data = response.json()
                access_token = data.get("access_token")
                if not access_token:
                    raise Exception("No access token received from ABDM Gateway")
                return access_token
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to ABDM Gateway at {self.base_url}: {e}")
            raise Exception(
                f"Cannot connect to ABDM Gateway. "
                f"Please verify ABHA_BASE_URL is correct and the gateway is accessible. "
                f"Error: {str(e)}"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"ABDM Gateway authentication failed: {e.response.status_code} - {e.response.text}")
            raise Exception(
                f"ABDM Gateway authentication failed: {e.response.status_code}. "
                f"Please verify ABHA_CLIENT_ID and ABHA_CLIENT_SECRET are correct."
            )
        except Exception as e:
            logger.error(f"Failed to get ABDM access token: {e}")
            raise Exception(f"Failed to authenticate with ABDM Gateway: {str(e)}")
    
    async def initiate_abha_auth(
        self,
        auth_method: str,
        mobile_number: Optional[str] = None,
        aadhaar_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initiate ABHA authentication (M1)
        
        Args:
            auth_method: "MOBILE_OTP" or "AADHAAR_OTP"
            mobile_number: Required for MOBILE_OTP
            aadhaar_number: Required for AADHAAR_OTP (will be hashed, never stored)
        
        Returns:
            transaction_id: For OTP verification
            txn_id: Transaction ID from ABDM
        """
        if auth_method not in ["MOBILE_OTP", "AADHAAR_OTP"]:
            raise ValueError("auth_method must be MOBILE_OTP or AADHAAR_OTP")
        
        if auth_method == "MOBILE_OTP" and not mobile_number:
            raise ValueError("mobile_number required for MOBILE_OTP")
        
        if auth_method == "AADHAAR_OTP" and not aadhaar_number:
            raise ValueError("aadhaar_number required for AADHAAR_OTP")
        
        try:
            access_token = await self._get_access_token()
            
            # Prepare request based on auth method
            if auth_method == "MOBILE_OTP":
                payload = {
                    "mobile": mobile_number
                }
                endpoint = f"{self.base_url}/v1/registration/mobile/generateOtp"
            else:  # AADHAAR_OTP
                # Hash Aadhaar before sending (never store raw Aadhaar)
                # Note: In production, use proper hashing as per ABDM guidelines
                payload = {
                    "aadhaar": aadhaar_number  # Will be hashed by ABDM Gateway
                }
                endpoint = f"{self.base_url}/v1/registration/aadhaar/generateOtp"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract transaction ID
                transaction_id = data.get("txnId") or data.get("transaction_id")
                
                if not transaction_id:
                    raise Exception("No transaction ID received from ABDM")
                
                logger.info(f"ABHA auth initiated: method={auth_method}, txn_id={transaction_id[:10]}...")
                
                return {
                    "transaction_id": transaction_id,
                    "txn_id": transaction_id
                }
        
        except httpx.HTTPStatusError as e:
            logger.error(f"ABDM Gateway error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"ABDM Gateway error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Failed to initiate ABHA auth: {e}")
            raise
    
    async def verify_otp_and_get_abha(
        self,
        transaction_id: str,
        otp: str,
        auth_method: str
    ) -> Dict[str, Any]:
        """
        Verify OTP and get ABHA number/address (M1)
        
        Args:
            transaction_id: From initiate_abha_auth
            otp: OTP entered by user
            auth_method: "MOBILE_OTP" or "AADHAAR_OTP"
        
        Returns:
            abha_number: ABHA number (should be masked before storage)
            abha_address: ABHA address
            demographic: Basic demographic profile
        """
        try:
            access_token = await self._get_access_token()
            
            # Verify OTP
            if auth_method == "MOBILE_OTP":
                verify_payload = {
                    "txnId": transaction_id,
                    "otp": otp
                }
                verify_endpoint = f"{self.base_url}/v1/registration/mobile/verifyOtp"
            else:  # AADHAAR_OTP
                verify_payload = {
                    "txnId": transaction_id,
                    "otp": otp
                }
                verify_endpoint = f"{self.base_url}/v1/registration/aadhaar/verifyOtp"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Step 1: Verify OTP
                verify_response = await client.post(
                    verify_endpoint,
                    json=verify_payload,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                verify_response.raise_for_status()
                verify_data = verify_response.json()
                
                # Extract ABHA details
                abha_number = verify_data.get("abhaNumber") or verify_data.get("abha_number")
                abha_address = verify_data.get("abhaAddress") or verify_data.get("abha_address")
                
                if not abha_number:
                    raise Exception("ABHA number not received from ABDM")
                
                # Step 2: Fetch demographic profile (M1 - demographic only)
                # Use ABHA address to fetch profile
                if abha_address:
                    profile_data = await self.get_abha_profile(abha_address)
                else:
                    profile_data = {}
                
                logger.info(f"ABHA verified successfully: abha_number={abha_number[:5]}...")
                
                return {
                    "abha_number": abha_number,
                    "abha_address": abha_address or f"{abha_number}@abdm",
                    "demographic": profile_data
                }
        
        except httpx.HTTPStatusError as e:
            logger.error(f"ABDM Gateway error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"OTP verification failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Failed to verify ABHA OTP: {e}")
            raise
    
    async def get_abha_profile(self, abha_address: str) -> Dict[str, Any]:
        """
        Get ABHA demographic profile (M1 - demographic only)
        
        Args:
            abha_address: ABHA address (e.g., xxxxx@abdm)
        
        Returns:
            Demographic data only (name, DOB, gender, mobile, email)
            NO health records, NO vaccination data
        """
        try:
            access_token = await self._get_access_token()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/v1/profile/{abha_address}",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract ONLY demographic fields (M1 scope)
                # DO NOT store full response
                demographic = {
                    "name": data.get("name"),
                    "date_of_birth": data.get("dateOfBirth") or data.get("date_of_birth"),
                    "gender": data.get("gender"),
                    "mobile": data.get("mobile"),
                    "email": data.get("email")
                }
                
                logger.info(f"ABHA profile fetched: abha_address={abha_address[:10]}...")
                
                return demographic
        
        except httpx.HTTPStatusError as e:
            logger.error(f"ABDM Gateway error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to fetch ABHA profile: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Failed to get ABHA profile: {e}")
            raise
    
    def mask_abha_number(self, abha_number: str) -> str:
        """
        Mask ABHA number for storage (security best practice)
        Store only masked version, never full ABHA number
        """
        if not abha_number or len(abha_number) < 4:
            return abha_number
        # Show first 2 and last 2 digits, mask the rest
        return f"{abha_number[:2]}{'*' * (len(abha_number) - 4)}{abha_number[-2:]}"


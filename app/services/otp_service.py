"""OTP Service for handling OTP generation, validation, and SMS delivery"""
import hashlib
import secrets
import logging
from typing import Optional
from datetime import datetime, timedelta
from redis.asyncio import Redis

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)


class OTPService:
    """Service for OTP operations"""
    
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 3
    MAX_ATTEMPTS = 3
    RATE_LIMIT_WINDOW_SECONDS = 60  # 1 minute
    MAX_OTP_REQUESTS_PER_WINDOW = 3
    
    def __init__(self, redis: Redis):
        self.redis = redis
    
    async def generate_otp(self, mobile_number: str) -> str:
        """Generate a random 6-digit OTP"""
        otp = ''.join([str(secrets.randbelow(10)) for _ in range(self.OTP_LENGTH)])
        return otp
    
    def hash_otp(self, otp: str) -> str:
        """Hash OTP before storing"""
        return hashlib.sha256(otp.encode()).hexdigest()
    
    async def check_rate_limit(self, mobile_number: str) -> bool:
        """Check if user has exceeded rate limit"""
        # Normalize mobile number
        mobile_number = mobile_number.strip()
        key = f"otp:rate_limit:{mobile_number}"
        count = await self.redis.get(key)
        
        if count and int(count) >= self.MAX_OTP_REQUESTS_PER_WINDOW:
            return False
        
        return True
    
    async def increment_rate_limit(self, mobile_number: str):
        """Increment rate limit counter"""
        # Normalize mobile number
        mobile_number = mobile_number.strip()
        key = f"otp:rate_limit:{mobile_number}"
        current = await self.redis.get(key)
        
        if current:
            await self.redis.incr(key)
        else:
            await self.redis.setex(key, self.RATE_LIMIT_WINDOW_SECONDS, "1")
    
    async def store_otp(self, mobile_number: str, otp: str):
        """Store OTP in Redis with expiry"""
        # Normalize mobile number (remove whitespace, ensure consistent format)
        mobile_number = mobile_number.strip()
        hashed_otp = self.hash_otp(otp)
        key = f"otp:{mobile_number}"
        attempts_key = f"otp:attempts:{mobile_number}"
        
        # Store hashed OTP with expiry (as string, Redis will handle encoding)
        await self.redis.setex(
            key,
            self.OTP_EXPIRY_MINUTES * 60,
            hashed_otp
        )
        
        # Reset attempts counter
        await self.redis.setex(
            attempts_key,
            self.OTP_EXPIRY_MINUTES * 60,
            "0"  # Store as string
        )
        
        logger.info(f"OTP stored for mobile: {self._mask_mobile(mobile_number)}, key: {key}")
    
    async def verify_otp(self, mobile_number: str, otp: str, invalidate_on_success: bool = True) -> bool:
        """
        Verify OTP
        
        Args:
            mobile_number: Mobile number
            otp: OTP to verify
            invalidate_on_success: If True, delete OTP after successful verification (default: True)
                                   Set to False if you want to keep OTP until full auth flow completes
        """
        # Normalize mobile number (remove whitespace, ensure consistent format)
        mobile_number = mobile_number.strip()
        key = f"otp:{mobile_number}"
        attempts_key = f"otp:attempts:{mobile_number}"
        
        # Check if OTP exists
        stored_hash = await self.redis.get(key)
        if not stored_hash:
            logger.warning(f"OTP not found or expired for {self._mask_mobile(mobile_number)}, key: {key}")
            return False
        
        # Check attempts
        attempts = await self.redis.get(attempts_key)
        if attempts and int(attempts) >= self.MAX_ATTEMPTS:
            logger.warning(f"Max OTP attempts exceeded for {self._mask_mobile(mobile_number)}")
            await self.invalidate_otp(mobile_number)
            return False
        
        # Verify OTP
        hashed_input = self.hash_otp(otp)
        # Handle both bytes and string (depending on Redis config)
        # With decode_responses=True, Redis returns strings, not bytes
        stored_hash_str = stored_hash.decode() if isinstance(stored_hash, bytes) else str(stored_hash).strip()
        hashed_input_str = str(hashed_input).strip()
        
        # Debug logging
        logger.info(
            f"OTP verification for {self._mask_mobile(mobile_number)} - "
            f"Input OTP: {otp}, "
            f"Hashed input: {hashed_input_str[:20]}..., "
            f"Stored hash: {stored_hash_str[:20] if stored_hash_str else 'None'}..., "
            f"Match: {hashed_input_str == stored_hash_str}"
        )
        
        if hashed_input_str == stored_hash_str:
            # OTP is valid
            if invalidate_on_success:
                # Delete it to prevent reuse
                await self.invalidate_otp(mobile_number)
            logger.info(f"OTP verified successfully for {self._mask_mobile(mobile_number)}")
            return True
        else:
            # Increment attempts
            await self.redis.incr(attempts_key)
            logger.warning(
                f"Invalid OTP attempt for {self._mask_mobile(mobile_number)}. "
                f"Expected hash: {stored_hash_str[:30] if stored_hash_str else 'None'}..., "
                f"Got hash: {hashed_input_str[:30]}..."
            )
            return False
    
    async def invalidate_otp(self, mobile_number: str):
        """Invalidate OTP after use or max attempts"""
        key = f"otp:{mobile_number}"
        attempts_key = f"otp:attempts:{mobile_number}"
        await self.redis.delete(key, attempts_key)
    
    async def send_otp(self, mobile_number: str, otp: str) -> bool:
        """Send OTP via SMS provider"""
        try:
            # Get SMS provider
            provider = SMSProviderFactory.get_provider()
            
            # Send OTP
            success = await provider.send_otp(mobile_number, otp)
            
            if success:
                logger.info(f"OTP sent successfully to {self._mask_mobile(mobile_number)}")
            else:
                logger.error(f"Failed to send OTP to {self._mask_mobile(mobile_number)}")
            
            return success
        except Exception as e:
            logger.error(f"Error sending OTP: {str(e)}")
            return False
    
    def _mask_mobile(self, mobile_number: str) -> str:
        """Mask mobile number for logging"""
        if len(mobile_number) > 4:
            return f"****{mobile_number[-4:]}"
        return "****"


# SMS Provider Abstraction
class SMSProvider:
    """Base SMS Provider interface"""
    
    async def send_otp(self, mobile_number: str, otp: str) -> bool:
        raise NotImplementedError


class Msg91Provider(SMSProvider):
    """MSG91 SMS Provider"""
    
    async def send_otp(self, mobile_number: str, otp: str) -> bool:
        """Send OTP via MSG91"""
        import aiohttp
        
        try:
            url = "https://api.msg91.com/api/v5/otp"
            params = {
                "template_id": settings.MSG91_TEMPLATE_ID,
                "mobile": mobile_number,
                "authkey": settings.MSG91_AUTH_KEY,
                "otp": otp
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, params=params) as response:
                    if response.status == 200:
                        return True
                    else:
                        logger.error(f"MSG91 API error: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"MSG91 send error: {str(e)}")
            return False


class GupshupProvider(SMSProvider):
    """Gupshup SMS Provider"""
    
    async def send_otp(self, mobile_number: str, otp: str) -> bool:
        """Send OTP via Gupshup"""
        import aiohttp
        
        try:
            url = "https://api.gupshup.io/sm/api/v1/msg"
            headers = {
                "apikey": settings.GUPSHUP_API_KEY,
                "Content-Type": "application/x-www-form-urlencoded"
            }
            data = {
                "channel": "sms",
                "source": settings.GUPSHUP_SOURCE,
                "destination": mobile_number,
                "message": f"Your OTP is {otp}. Valid for 3 minutes. Do not share with anyone.",
                "src.name": settings.APP_NAME
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=data) as response:
                    if response.status == 200:
                        return True
                    else:
                        logger.error(f"Gupshup API error: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Gupshup send error: {str(e)}")
            return False


class ConsoleSMSProvider(SMSProvider):
    """Console SMS Provider for development/testing"""
    
    async def send_otp(self, mobile_number: str, otp: str) -> bool:
        """Print OTP to console (for development only)"""
        logger.info(f"📱 SMS TO: {mobile_number}")
        logger.info(f"🔐 OTP: {otp}")
        logger.info(f"⏰ Valid for {OTPService.OTP_EXPIRY_MINUTES} minutes")
        print(f"\n{'='*60}")
        print(f"{' '*10}📱 OTP FOR {mobile_number}")
        print(f"{' '*10}🔐 YOUR OTP IS: {otp}")
        print(f"{' '*10}⏰ Valid for {OTPService.OTP_EXPIRY_MINUTES} minutes")
        print(f"{'='*60}\n")
        return True


class SMSProviderFactory:
    """Factory to get SMS provider based on configuration"""
    
    @staticmethod
    def get_provider() -> SMSProvider:
        """Get SMS provider instance"""
        provider_name = getattr(settings, 'SMS_PROVIDER', 'console').lower()
        
        if provider_name == 'msg91':
            return Msg91Provider()
        elif provider_name == 'gupshup':
            return GupshupProvider()
        else:
            # Default to console for development
            return ConsoleSMSProvider()



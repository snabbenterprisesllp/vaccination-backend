"""QR Code generation service"""
import qrcode
from io import BytesIO
from typing import Optional
import base64
import logging

from app.utils.gcs_client import GCSClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class QRCodeService:
    """QR Code generation and management"""
    
    def __init__(self):
        self.gcs_client = GCSClient()
    
    async def generate_qr_code(
        self,
        data: str,
        child_id: int
    ) -> Optional[str]:
        """Generate QR code and upload to GCS (or return base64 if GCS unavailable)"""
        try:
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            
            # Add data (QR token)
            qr_data = f"{settings.API_VERSION}/children/qr/{data}"
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to bytes
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            qr_bytes = buffer.read()
            
            # Try to upload to GCS if available
            if self.gcs_client.bucket:
                try:
                    file_path = f"qr-codes/child-{child_id}-{data[:8]}.png"
                    url = await self.gcs_client.upload_file(
                        file_data=qr_bytes,
                        destination_path=file_path,
                        content_type="image/png"
                    )
                    logger.info(f"QR code uploaded to GCS for child {child_id}")
                    return url
                except Exception as e:
                    logger.warning(f"Failed to upload QR code to GCS: {e}. Using base64 fallback.")
            
            # Fallback: Return base64 data URL if GCS is not available
            img_base64 = base64.b64encode(qr_bytes).decode()
            data_url = f"data:image/png;base64,{img_base64}"
            logger.info(f"QR code generated as base64 for child {child_id} (GCS not available)")
            return data_url
            
        except Exception as e:
            logger.error(f"Failed to generate QR code: {e}")
            return None
    
    def generate_qr_base64(self, data: str) -> str:
        """Generate QR code as base64 string"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.read()).decode()
        return f"data:image/png;base64,{img_base64}"


"""
Validation utilities for email and mobile number
Follows RFC 5322 for email and E.164 for mobile numbers
"""
import re
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Disposable email domains (configurable list)
DISPOSABLE_EMAIL_DOMAINS = {
    'tempmail.com', 'guerrillamail.com', 'mailinator.com', '10minutemail.com',
    'throwaway.email', 'temp-mail.org', 'getnada.com', 'mohmal.com',
    'fakeinbox.com', 'trashmail.com', 'yopmail.com', 'sharklasers.com',
    'mintemail.com', 'meltmail.com', 'spamgourmet.com', 'emailondeck.com'
}

# Country code patterns (E.164 format)
COUNTRY_CODES = {
    'IN': {'code': '+91', 'length': 10, 'pattern': r'^\+91[6-9]\d{9}$'},  # India
    'US': {'code': '+1', 'length': 10, 'pattern': r'^\+1\d{10}$'},  # USA/Canada
    'UK': {'code': '+44', 'length': 10, 'pattern': r'^\+44\d{10,11}$'},  # UK
    # Add more countries as needed
}

# RFC 5322 compliant email regex (simplified but robust)
EMAIL_PATTERN = re.compile(
    r'^[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?@'
    r'[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$'
)

# More strict RFC 5322 pattern (for backend)
STRICT_EMAIL_PATTERN = re.compile(
    r'^[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+)*@'
    r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
)


def validate_email(email: str, check_disposable: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Validate email address
    
    Args:
        email: Email address to validate
        check_disposable: Whether to check for disposable email domains
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    # Normalize: trim and lowercase
    email = email.strip().lower()
    
    if not email:
        return False, "Email cannot be empty"
    
    # Check for spaces
    if ' ' in email:
        return False, "Invalid email format"
    
    # Check for single @
    if email.count('@') != 1:
        return False, "Invalid email format"
    
    # Split email
    local_part, domain = email.split('@', 1)
    
    # Validate local part
    if not local_part or len(local_part) > 64:
        return False, "Invalid email format"
    
    # Validate domain
    if not domain or len(domain) > 255:
        return False, "Invalid email format"
    
    # Check domain has at least one dot
    if '.' not in domain:
        return False, "Invalid email format"
    
    # Check TLD
    tld = domain.split('.')[-1]
    if len(tld) < 2 or not tld.isalpha():
        return False, "Invalid email format"
    
    # RFC 5322 pattern validation
    if not STRICT_EMAIL_PATTERN.match(email):
        return False, "Invalid email format"
    
    # Check disposable email domains
    if check_disposable:
        domain_lower = domain.lower()
        if domain_lower in DISPOSABLE_EMAIL_DOMAINS:
            return False, "Disposable email addresses are not allowed"
    
    return True, None


def normalize_email(email: str) -> str:
    """
    Normalize email address (lowercase, trim)
    
    Args:
        email: Email address to normalize
    
    Returns:
        Normalized email address
    """
    if not email:
        return ""
    return email.strip().lower()


def validate_mobile_number(mobile: str, default_country: str = 'IN') -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate mobile number and normalize to E.164 format
    
    Args:
        mobile: Mobile number to validate
        default_country: Default country code if not provided (default: 'IN' for India)
    
    Returns:
        Tuple of (is_valid, normalized_number, error_message)
    """
    if not mobile:
        return False, None, "Mobile number is required"
    
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', mobile.strip())
    
    if not cleaned:
        return False, None, "Invalid mobile number"
    
    # Check if it starts with +
    if cleaned.startswith('+'):
        # Has country code
        # Extract country code and number
        if len(cleaned) < 8:  # Minimum: +1 + 7 digits
            return False, None, "Invalid mobile number"
        
        # Try to match known country patterns
        normalized = cleaned
        for country, config in COUNTRY_CODES.items():
            if cleaned.startswith(config['code']):
                number_part = cleaned[len(config['code']):]
                if re.match(r'^\d{' + str(config['length']) + r'}$', number_part):
                    return True, normalized, None
        
        # Generic E.164 validation (7-15 digits after country code)
        number_part = cleaned[1:]  # Remove +
        if len(number_part) < 7 or len(number_part) > 15:
            return False, None, "Invalid mobile number"
        
        # Check if all digits after +
        if not number_part.isdigit():
            return False, None, "Invalid mobile number"
        
        return True, normalized, None
    else:
        # No country code, assume default country
        if not cleaned.isdigit():
            return False, None, "Invalid mobile number"
        
        country_config = COUNTRY_CODES.get(default_country)
        if not country_config:
            return False, None, "Please enter a valid country code"
        
        # Validate length for default country
        if len(cleaned) != country_config['length']:
            return False, None, f"Mobile number must be {country_config['length']} digits for {default_country}"
        
        # For India, first digit should be 6-9
        if default_country == 'IN' and cleaned[0] not in '6789':
            return False, None, "Invalid mobile number. Indian numbers must start with 6, 7, 8, or 9"
        
        # Normalize to E.164 format
        normalized = country_config['code'] + cleaned
        return True, normalized, None


def normalize_mobile_number(mobile: str, default_country: str = 'IN') -> str:
    """
    Normalize mobile number to E.164 format
    
    Args:
        mobile: Mobile number to normalize
        default_country: Default country code if not provided
    
    Returns:
        Normalized mobile number in E.164 format
    """
    is_valid, normalized, _ = validate_mobile_number(mobile, default_country)
    if is_valid and normalized:
        return normalized
    return mobile  # Return original if validation fails (should be validated first)


def mask_email(email: str) -> str:
    """
    Mask email address for privacy (e.g., u***@example.com)
    
    Args:
        email: Email address to mask
    
    Returns:
        Masked email address
    """
    if not email or '@' not in email:
        return "***"
    
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        masked_local = local[0] + "***"
    else:
        masked_local = local[0] + "***" + local[-1]
    
    return f"{masked_local}@{domain}"


def mask_mobile(mobile: str) -> str:
    """
    Mask mobile number for privacy (e.g., +91******890)
    
    Args:
        mobile: Mobile number to mask
    
    Returns:
        Masked mobile number
    """
    if not mobile:
        return "***"
    
    # Remove + for processing
    cleaned = mobile.replace('+', '')
    
    if len(cleaned) <= 4:
        return "****"
    
    # Show country code and last 3 digits
    if mobile.startswith('+'):
        country_code = mobile[:3]  # +91, +1, etc.
        last_digits = cleaned[-3:]
        masked = '*' * (len(cleaned) - 3)
        return f"{country_code}{masked}{last_digits}"
    else:
        last_digits = cleaned[-3:]
        masked = '*' * (len(cleaned) - 3)
        return f"{masked}{last_digits}"



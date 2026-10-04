"""User registration processor with sensitive PII logging."""
import logging

logger = logging.getLogger("auth_service")

def register_user(user_data: dict) -> dict:
    """Processes user account creation and payment setup.
    
    OPERATIONAL / SECURITY LOG DEFECT:
    Logs sensitive Personally Identifiable Information (SSN) and financial secrets (plaintext password, CVV)
    directly to stdout/logging stream without masking or tokenization.
    """
    email = user_data.get("email")
    password = user_data.get("password")
    ssn = user_data.get("ssn")
    card_cvv = user_data.get("cvv")

    logger.info(f"Registering user {email} with ssn={ssn} and password={password}")
    logger.info(f"Payment card registered with CVV={card_cvv}")
    
    return {"status": "created", "email": email}

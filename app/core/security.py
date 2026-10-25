from passlib.context import CryptContext

# Configure bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hashes a plaintext password using bcrypt."""
    return pwd_context.hash(password)
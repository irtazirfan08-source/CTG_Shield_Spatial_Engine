import pytest
from fastapi.testclient import TestClient
from main import app
import auth_utils

client = TestClient(app)


def test_password_hashing_and_verification():
    """Verify bcrypt hashing generates valid salted hashes and matches correctly."""
    raw_password = "CtgShieldSecretPass2026!"
    
    # Resolve hashing function name dynamically to match implementation
    if hasattr(auth_utils, "hash_password"):
        hashed = auth_utils.hash_password(raw_password)
    elif hasattr(auth_utils, "get_password_hash"):
        hashed = auth_utils.get_password_hash(raw_password)
    else:
        pytest.fail("No password hashing function found in auth_utils.py")

    assert hashed != raw_password
    assert auth_utils.verify_password(raw_password, hashed) is True
    assert auth_utils.verify_password("WrongPassword123!", hashed) is False


def test_jwt_token_generation_and_payload():
    """Verify JWT access tokens encode data and generate non-empty strings."""
    test_payload = {"sub": "citizen_001@ctg.gov.bd", "role": "citizen"}
    
    if hasattr(auth_utils, "create_access_token"):
        token = auth_utils.create_access_token(data=test_payload)
        assert isinstance(token, str)
        assert len(token) > 30
        assert token.count(".") == 2  # Standard JWT header.payload.signature structure
    else:
        pytest.fail("create_access_token function not found in auth_utils.py")


def test_swagger_documentation_endpoint():
    """Ensure FastAPI docs and schema are served correctly without server crashes."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "Swagger UI" in response.text


def test_auth_login_rejects_empty_payload():
    """Ensure POST /api/v1/auth/login validates incoming schema and rejects empty requests."""
    response = client.post("/api/v1/auth/login", json={})
    assert response.status_code in [400, 422]


def test_auth_register_rejects_malformed_email():
    """Ensure POST /api/v1/auth/register rejects invalid email structures."""
    malformed_payload = {
        "email": "not-an-email",
        "password": "ValidPassword123!"
    }
    response = client.post("/api/v1/auth/register", json=malformed_payload)
    assert response.status_code in [400, 422]


def test_spatial_evaluate_endpoint_parameter_validation():
    """Ensure /api/v1/safety/evaluate-location requires valid GPS latitude/longitude query params."""
    response = client.get("/api/v1/safety/evaluate-location")
    # Must fail validation because required latitude and longitude query params are missing
    assert response.status_code in [400, 422]
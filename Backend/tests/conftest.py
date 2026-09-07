import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Provide dummy env vars if not present
os.environ.setdefault("SUPABASE_URL", "https://mock-test-project.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "mock-anon-key-for-testing")

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)

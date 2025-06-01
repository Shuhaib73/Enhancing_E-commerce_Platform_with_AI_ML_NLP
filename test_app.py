import os 
import pytest 

from app import app 

@pytest.fixture
def client():
    # Setup the Flask test client..
    with app.test_client() as client:
        yield client

def test_home(client):
    response = client.get("/")
    assert response.status_code == 200

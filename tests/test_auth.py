from sqlalchemy import select

from app.models.user import User


def test_register_user(client, db_session, register_user):
    payload, response = register_user(email="test_register@example.com")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == payload["email"]
    assert "id" in data

    db_user = db_session.scalars(select(User).where(User.email == payload["email"])).first()
    assert db_user is not None
    assert db_user.email == payload["email"]


def test_login_user(client, register_user, login_user):
    payload, response = register_user(email="login_user@example.com")
    assert response.status_code == 200

    login_response = login_user(payload["email"], payload["password"])
    assert login_response.status_code == 200
    data = login_response.json()
    assert "token" in data
    assert data["token_type"] == "Bearer"


def test_login_invalid_credentials(client, login_user):
    response = login_user("wrong@example.com", "wrongpassword")
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_register_with_existing_email_should_fail(client, register_user):
    payload, first_response = register_user(email="duplicate@example.com")
    assert first_response.status_code == 200

    second_response = client.post("/users/register", json=payload)
    assert second_response.status_code == 400
    assert second_response.json()["detail"] == "User with this email already exists"


def test_get_current_user_without_token_should_fail(client):
    response = client.get("/users/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid Authorization header"


def test_get_current_user_success(client, user_token, auth_headers):
    response = client.get("/users/me", headers=auth_headers(user_token))
    assert response.status_code == 200
    data = response.json()
    assert data["email"].endswith("@example.com")
    assert data["role"] == "customer"


def test_update_current_user_success(client, user_token, auth_headers):
    response = client.put(
        "/users/me",
        json={"first_name": "Updated", "phone": "19900001111"},
        headers=auth_headers(user_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["phone"] == "19900001111"

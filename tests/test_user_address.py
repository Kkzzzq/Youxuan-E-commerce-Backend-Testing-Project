from sqlalchemy import select

from app.models.address import Address


def test_add_address_success(client, db_session, user_token, auth_headers, create_address_for_user):
    headers = auth_headers(user_token)
    payload, response = create_address_for_user(headers, street="88 First Ave")
    assert response.status_code == 200
    data = response.json()
    assert data["street"] == payload["street"]

    db_address = db_session.get(Address, data["id"])
    assert db_address is not None
    assert db_address.user_id == data["user_id"]
    assert db_address.street == "88 First Ave"


def test_update_address_success(client, db_session, user_token, auth_headers, create_address_for_user):
    headers = auth_headers(user_token)
    _, create_response = create_address_for_user(headers, street="Old Street", city="Old City")
    address_id = create_response.json()["id"]

    update_response = client.put(
        f"/users/me/address/{address_id}",
        json={"street": "New Street", "city": "New City", "is_default": True},
        headers=headers,
    )
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["street"] == "New Street"
    assert data["city"] == "New City"
    assert data["is_default"] is True

    db_address = db_session.get(Address, address_id)
    assert db_address.street == "New Street"
    assert db_address.city == "New City"
    assert db_address.is_default is True


def test_order_with_other_users_address_should_fail(
    client,
    register_user,
    login_user,
    auth_headers,
    create_address_for_user,
    create_product_in_db,
    add_item_to_cart,
):
    user_a_payload, user_a_register = register_user(email="user_a@example.com")
    assert user_a_register.status_code == 200
    user_a_login = login_user(user_a_payload["email"], user_a_payload["password"])
    user_a_headers = auth_headers(user_a_login.json()["token"])
    _, address_response = create_address_for_user(user_a_headers, street="A Street")
    address_id = address_response.json()["id"]

    user_b_payload, user_b_register = register_user(email="user_b@example.com")
    assert user_b_register.status_code == 200
    user_b_login = login_user(user_b_payload["email"], user_b_payload["password"])
    user_b_headers = auth_headers(user_b_login.json()["token"])

    product = create_product_in_db(stock_quantity=10)
    cart_response = add_item_to_cart(product_id=product.id, quantity=1, headers=user_b_headers)
    assert cart_response.status_code == 200

    response = client.post(
        "/order",
        json={"shipping_address_id": address_id, "billing_address_id": address_id},
        headers=user_b_headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid address"

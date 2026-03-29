from sqlalchemy import select

from app.models.cart import Cart
from app.models.cart_item import CartItem


def test_get_empty_cart_for_authenticated_user(client, user_token, auth_headers):
    response = client.get("/cart", headers=auth_headers(user_token))
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total_items"] == 0
    assert float(data["subtotal"]) == 0.0


def test_add_item_to_cart_success(client, create_product_in_db, user_token, auth_headers):
    product = create_product_in_db(stock_quantity=10)
    add_response = client.post(
        "/cart/items",
        json={"product_id": product.id, "quantity": 2},
        headers=auth_headers(user_token),
    )
    assert add_response.status_code == 200

    cart_response = client.get("/cart", headers=auth_headers(user_token))
    assert cart_response.status_code == 200
    data = cart_response.json()
    assert data["total_items"] == 2
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == product.id
    assert data["items"][0]["quantity"] == 2


def test_update_cart_item_quantity_success(client, create_product_in_db, user_token, auth_headers):
    headers = auth_headers(user_token)
    product = create_product_in_db(stock_quantity=20)
    add_response = client.post(
        "/cart/items", json={"product_id": product.id, "quantity": 1}, headers=headers
    )
    item_id = add_response.json()["item_id"]

    update_response = client.put(
        f"/cart/items/{item_id}", json={"quantity": 4}, headers=headers
    )
    assert update_response.status_code == 200

    cart_response = client.get("/cart", headers=headers)
    assert cart_response.json()["items"][0]["quantity"] == 4


def test_remove_cart_item_success(client, create_product_in_db, user_token, auth_headers):
    headers = auth_headers(user_token)
    product = create_product_in_db(stock_quantity=10)
    add_response = client.post(
        "/cart/items", json={"product_id": product.id, "quantity": 1}, headers=headers
    )
    item_id = add_response.json()["item_id"]

    remove_response = client.delete(f"/cart/items/{item_id}", headers=headers)
    assert remove_response.status_code == 200
    assert remove_response.json()["message"] == "Item removed"

    cart_response = client.get("/cart", headers=headers)
    assert cart_response.json()["items"] == []
    assert cart_response.json()["total_items"] == 0


def test_guest_cart_creates_session_cookie(client):
    response = client.get("/cart")
    assert response.status_code == 200
    assert response.cookies.get("session_id") is not None
    assert client.cookies.get("session_id") is not None


def test_guest_add_item_to_cart_success(client, create_product_in_db):
    cart_response = client.get("/cart")
    assert cart_response.status_code == 200
    product = create_product_in_db(stock_quantity=8)

    add_response = client.post("/cart/items", json={"product_id": product.id, "quantity": 3})
    assert add_response.status_code == 200

    latest_cart = client.get("/cart")
    data = latest_cart.json()
    assert data["total_items"] == 3
    assert data["items"][0]["product_id"] == product.id


def test_guest_cart_merged_after_login(
    client,
    db_session,
    create_product_in_db,
    register_user,
    login_user,
    auth_headers,
):
    first_cart_response = client.get("/cart")
    session_id = first_cart_response.cookies.get("session_id")
    assert session_id is not None

    product = create_product_in_db(stock_quantity=12)
    add_response = client.post("/cart/items", json={"product_id": product.id, "quantity": 2})
    assert add_response.status_code == 200

    payload, register_response = register_user(email="guest_merge@example.com")
    assert register_response.status_code == 200
    login_response = login_user(payload["email"], payload["password"])
    headers = auth_headers(login_response.json()["token"])

    merged_cart_response = client.get("/cart", headers=headers)
    assert merged_cart_response.status_code == 200
    data = merged_cart_response.json()
    assert data["total_items"] == 2
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == product.id

    merged_cart = db_session.scalars(select(Cart).where(Cart.user_id.is_not(None))).first()
    assert merged_cart is not None
    assert merged_cart.session_id is None
    merged_item = db_session.scalars(select(CartItem).where(CartItem.cart_id == merged_cart.id)).first()
    assert merged_item is not None
    assert merged_item.product_id == product.id

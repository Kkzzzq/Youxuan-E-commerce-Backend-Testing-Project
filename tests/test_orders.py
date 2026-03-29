from sqlalchemy import select

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product


def test_create_order(client, db_session, order_factory):
    result = order_factory(cart_quantity=2, product_price=50.0)
    response = result["order_response"]
    assert response.status_code == 200
    data = response.json()
    assert data["total_amount"] == 100.0
    assert data["status"] == "pending"

    db_order = db_session.get(Order, data["id"])
    assert db_order is not None
    db_items = db_session.scalars(select(OrderItem).where(OrderItem.order_id == data["id"])).all()
    assert len(db_items) == 1


def test_get_orders(client, order_factory):
    result = order_factory(cart_quantity=1)
    assert result["order_response"].status_code == 200

    response = client.get("/order", headers=result["headers"])
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_checkout_with_empty_cart_should_fail(client, user_token, auth_headers, create_address_for_user):
    headers = auth_headers(user_token)
    _, address_response = create_address_for_user(headers)
    address_id = address_response.json()["id"]

    response = client.post(
        "/order",
        json={"shipping_address_id": address_id, "billing_address_id": address_id},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Your cart is empty."


def test_checkout_with_other_user_address_should_fail(
    client,
    register_user,
    login_user,
    auth_headers,
    create_address_for_user,
    create_product_in_db,
    add_item_to_cart,
):
    a_payload, a_register = register_user(email="order_a@example.com")
    assert a_register.status_code == 200
    a_login = login_user(a_payload["email"], a_payload["password"])
    a_headers = auth_headers(a_login.json()["token"])
    _, address_response = create_address_for_user(a_headers)
    address_id = address_response.json()["id"]

    b_payload, b_register = register_user(email="order_b@example.com")
    assert b_register.status_code == 200
    b_login = login_user(b_payload["email"], b_payload["password"])
    b_headers = auth_headers(b_login.json()["token"])

    product = create_product_in_db(stock_quantity=5)
    add_response = add_item_to_cart(product.id, headers=b_headers)
    assert add_response.status_code == 200

    response = client.post(
        "/order",
        json={"shipping_address_id": address_id, "billing_address_id": address_id},
        headers=b_headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid address"


def test_checkout_with_insufficient_stock_should_fail(
    client,
    db_session,
    user_token,
    auth_headers,
    create_address_for_user,
    create_product_in_db,
    add_item_to_cart,
):
    headers = auth_headers(user_token)
    _, address_response = create_address_for_user(headers)
    address_id = address_response.json()["id"]
    product = create_product_in_db(stock_quantity=2, price=30.0)

    add_response = add_item_to_cart(product.id, quantity=2, headers=headers)
    assert add_response.status_code == 200

    db_product = db_session.get(Product, product.id)
    db_product.stock_quantity = 1
    db_session.commit()

    response = client.post(
        "/order",
        json={"shipping_address_id": address_id, "billing_address_id": address_id},
        headers=headers,
    )
    assert response.status_code == 400
    assert "Not enough stock" in response.json()["detail"]


def test_checkout_clears_cart_after_success(client, db_session, order_factory):
    result = order_factory(cart_quantity=2)
    response = result["order_response"]
    assert response.status_code == 200

    cart = db_session.scalars(select(Cart).where(Cart.user_id.is_not(None))).first()
    remaining_items = [] if cart is None else db_session.scalars(select(CartItem).where(CartItem.cart_id == cart.id)).all()
    assert remaining_items == []


def test_checkout_reduces_stock_after_success(client, db_session, order_factory):
    result = order_factory(stock_quantity=10, cart_quantity=3, product_price=25.0)
    response = result["order_response"]
    assert response.status_code == 200

    db_product = db_session.get(Product, result["product"].id)
    assert db_product.stock_quantity == 7


def test_get_single_order_success(client, order_factory):
    result = order_factory(cart_quantity=1)
    order_id = result["order_response"].json()["id"]

    response = client.get(f"/order/{order_id}", headers=result["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == order_id
    assert len(data["order_items"]) == 1


def test_get_other_users_order_should_fail(client, order_factory, register_user, login_user, auth_headers):
    owner_result = order_factory(email="owner_order@example.com", cart_quantity=1)
    order_id = owner_result["order_response"].json()["id"]

    other_payload, other_register = register_user(email="other_order@example.com")
    assert other_register.status_code == 200
    other_login = login_user(other_payload["email"], other_payload["password"])
    other_headers = auth_headers(other_login.json()["token"])

    response = client.get(f"/order/{order_id}", headers=other_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"

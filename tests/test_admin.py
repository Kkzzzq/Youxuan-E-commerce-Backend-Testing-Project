from app.models.order import Order


def test_normal_user_cannot_access_admin_orders(client, user_token, auth_headers):
    response = client.get("/admin/orders", headers=auth_headers(user_token))
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin privileges required"


def test_admin_can_list_orders(client, admin_token, admin_headers, order_factory):
    created = order_factory(email="admin_orders_target@example.com")
    assert created["order_response"].status_code == 200

    response = client.get("/admin/orders", headers=admin_headers(admin_token))
    assert response.status_code == 200
    data = response.json()
    assert "orders" in data
    assert data["total"] >= 1
    assert len(data["orders"]) >= 1


def test_admin_can_update_order_status(client, db_session, admin_token, admin_headers, order_factory):
    created = order_factory(email="admin_update_order@example.com")
    order_id = created["order_response"].json()["id"]

    response = client.patch(
        f"/admin/orders/{order_id}/status",
        json={"status": "delivered"},
        headers=admin_headers(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["new_status"] == "delivered"

    order = db_session.get(Order, order_id)
    assert order.status == "delivered"


def test_admin_can_mark_order_shipped(client, db_session, admin_token, admin_headers, order_factory):
    created = order_factory(email="admin_ship_order@example.com")
    order_id = created["order_response"].json()["id"]

    response = client.patch(
        f"/admin/orders/{order_id}/shipping",
        json={},
        headers=admin_headers(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["order_id"] == order_id

    order = db_session.get(Order, order_id)
    assert order.status == "shipped"
    assert order.shipped_at is not None

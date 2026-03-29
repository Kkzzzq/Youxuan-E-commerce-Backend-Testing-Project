from unittest.mock import MagicMock, patch

from app.models.order import Order
from app.models.payment import Payment


def create_paid_order(db_session, order_id: int):
    order = db_session.get(Order, order_id)
    order.payment_status = "success"
    order.status = "paid"
    db_session.commit()
    db_session.refresh(order)
    return order


def test_create_payment_intent(client, db_session, order_factory):
    result = order_factory(email="payment_user@example.com", cart_quantity=1, product_price=50.0)
    order_id = result["order_response"].json()["id"]

    with patch("stripe.PaymentIntent.create") as mock_create:
        mock_create.return_value = MagicMock(id="pi_12345", client_secret="secret_12345")
        response = client.post(
            "/payments/create-intent",
            json={"order_id": order_id},
            headers=result["headers"],
        )

    assert response.status_code == 200
    data = response.json()
    assert data["payment_intent_id"] == "pi_12345"
    assert data["client_secret"] == "secret_12345"

    payment = db_session.query(Payment).filter(Payment.transaction_id == "pi_12345").first()
    assert payment is not None
    assert payment.order_id == order_id
    assert payment.status == "pending"


def test_webhook_without_signature_should_fail(client):
    response = client.post(
        "/payments/webhook",
        content=b'{"type":"payment_intent.succeeded"}',
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Missing Stripe signature"


def test_create_payment_intent_for_nonexistent_order_should_fail(client, user_token, auth_headers):
    response = client.post(
        "/payments/create-intent",
        json={"order_id": 999999},
        headers=auth_headers(user_token),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_create_payment_intent_for_paid_order_should_fail(client, db_session, order_factory):
    result = order_factory(email="already_paid@example.com")
    order_id = result["order_response"].json()["id"]
    create_paid_order(db_session, order_id)

    response = client.post(
        "/payments/create-intent",
        json={"order_id": order_id},
        headers=result["headers"],
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Order already paid"


def test_payment_webhook_success_updates_payment_and_order(client, db_session, order_factory):
    result = order_factory(email="pay_success@example.com")
    order_id = result["order_response"].json()["id"]

    with patch("stripe.PaymentIntent.create") as mock_create:
        mock_create.return_value = MagicMock(id="pi_success", client_secret="secret_success")
        create_response = client.post(
            "/payments/create-intent",
            json={"order_id": order_id},
            headers=result["headers"],
        )
        assert create_response.status_code == 200

    with patch("stripe.Webhook.construct_event") as mock_construct:
        mock_construct.return_value = {
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": "pi_success"}},
        }
        response = client.post(
            "/payments/webhook",
            content=b'{"type":"payment_intent.succeeded"}',
            headers={"Stripe-Signature": "test_signature"},
        )

    assert response.status_code == 200
    payment = db_session.query(Payment).filter(Payment.transaction_id == "pi_success").first()
    order = db_session.get(Order, order_id)
    assert payment.status == "completed"
    assert order.payment_status == "success"
    assert order.status == "paid"


def test_payment_webhook_failed_event(client, db_session, order_factory):
    result = order_factory(email="pay_failed@example.com")
    order_id = result["order_response"].json()["id"]

    with patch("stripe.PaymentIntent.create") as mock_create:
        mock_create.return_value = MagicMock(id="pi_failed", client_secret="secret_failed")
        create_response = client.post(
            "/payments/create-intent",
            json={"order_id": order_id},
            headers=result["headers"],
        )
        assert create_response.status_code == 200

    with patch("stripe.Webhook.construct_event") as mock_construct:
        mock_construct.return_value = {
            "type": "payment_intent.payment_failed",
            "data": {"object": {"id": "pi_failed"}},
        }
        response = client.post(
            "/payments/webhook",
            content=b'{"type":"payment_intent.payment_failed"}',
            headers={"Stripe-Signature": "test_signature"},
        )

    assert response.status_code == 200
    payment = db_session.query(Payment).filter(Payment.transaction_id == "pi_failed").first()
    order = db_session.get(Order, order_id)
    assert payment.status == "failed"
    assert order.payment_status == "failed"

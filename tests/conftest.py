import os
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Test env must be configured before app imports
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_app.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-1234567890-testx")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_123")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_123")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("ELASTIC_URL", "http://localhost:9200")

from app.main import app
from app.db.database import Base
from app import models as app_models  # noqa: F401 - ensure all models are registered with Base metadata
from app.dependencies import get_db, get_redis_manager
from app.models.address import Address
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.user import User


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def get_json(self, key):
        return self.store.get(key)

    async def set_json(self, key, value, ex=None):
        self.store[key] = value

    async def delete(self, key):
        return 1 if self.store.pop(key, None) is not None else 0

    async def delete_pattern(self, pattern):
        keys = [key for key in self.store if key.startswith(pattern.rstrip("*"))]
        for key in keys:
            self.store.pop(key, None)
        return len(keys)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    fake_redis = FakeRedis()

    def override_get_db():
        yield db_session

    async def override_get_redis_manager():
        return fake_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_manager] = override_get_redis_manager

    with patch("app.main.redis_client.connect", new_callable=AsyncMock), patch(
        "app.main.redis_client.close", new_callable=AsyncMock
    ), patch("app.main.get_es_client", new_callable=AsyncMock), patch(
        "app.main.create_product_index", new_callable=AsyncMock
    ), patch("app.main.bulk_index_products", new_callable=AsyncMock), patch(
        "app.main.close_es_client", new_callable=AsyncMock
    ), patch("logging_loki.handlers.LokiHandler.emit", return_value=None), patch(
        "app.main.otlp_exporter.export", return_value=None
    ):
        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    def _build(token: str):
        return {"Authorization": f"Bearer {token}"}

    return _build


@pytest.fixture
def admin_headers():
    def _build(token: str):
        return {"Authorization": f"Bearer {token}"}

    return _build


@pytest.fixture
def registered_user_payload():
    def _build(email: str | None = None, **overrides):
        unique = uuid4().hex[:8]
        payload = {
            "email": email or f"user_{unique}@example.com",
            "password": "password123",
            "first_name": "Test",
            "last_name": "User",
            "phone": f"188{unique[:8]}",
        }
        payload.update(overrides)
        return payload

    return _build


@pytest.fixture
def registered_admin_payload(registered_user_payload):
    def _build(email: str | None = None, **overrides):
        payload = registered_user_payload(email=email, **overrides)
        payload.setdefault("first_name", "Admin")
        payload.setdefault("last_name", "User")
        return payload

    return _build


@pytest.fixture
def address_payload():
    def _build(**overrides):
        payload = {
            "type": "shipping",
            "street": "123 Test Street",
            "city": "San Jose",
            "state": "CA",
            "postal_code": "95112",
            "country": "US",
            "is_default": False,
        }
        payload.update(overrides)
        return payload

    return _build


@pytest.fixture
def product_payload():
    def _build(name: str | None = None, **overrides):
        unique = uuid4().hex[:8]
        payload = {
            "name": name or f"Test Product {unique}",
            "description": "A product created for API tests",
            "price": 99.99,
            "stock_quantity": 10,
            "image_url": "https://example.com/product.jpg",
            "is_active": True,
        }
        payload.update(overrides)
        return payload

    return _build


@pytest.fixture
def register_user(client, registered_user_payload):
    def _register(email: str | None = None, **overrides):
        payload = registered_user_payload(email=email, **overrides)
        response = client.post("/users/register", json=payload)
        return payload, response

    return _register


@pytest.fixture
def login_user(client):
    def _login(email: str, password: str = "password123"):
        payload = {"email": email, "password": password}
        response = client.post("/users/login", json=payload)
        return response

    return _login


@pytest.fixture
def promote_user_to_admin(db_session):
    def _promote(email: str):
        user = db_session.scalars(select(User).where(User.email == email)).first()
        assert user is not None, f"user not found for email={email}"
        user.role = "admin"
        db_session.commit()
        db_session.refresh(user)
        return user

    return _promote


@pytest.fixture
def create_product_in_db(db_session):
    def _create(**overrides):
        unique = uuid4().hex[:8]
        product = Product(
            name=overrides.pop("name", f"DB Product {unique}"),
            slug=overrides.pop("slug", f"db-product-{unique}"),
            description=overrides.pop("description", "Seeded test product"),
            price=overrides.pop("price", 49.99),
            stock_quantity=overrides.pop("stock_quantity", 20),
            sku=overrides.pop("sku", f"SKU-{unique.upper()}"),
            image_url=overrides.pop("image_url", "https://example.com/db-product.jpg"),
            is_active=overrides.pop("is_active", True),
            category_id=overrides.pop("category_id", None),
            **overrides,
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)
        return product

    return _create


@pytest.fixture
def create_address_for_user(client, address_payload):
    def _create(headers: dict, **overrides):
        payload = address_payload(**overrides)
        response = client.post("/users/me/address", json=payload, headers=headers)
        return payload, response

    return _create


@pytest.fixture
def add_item_to_cart(client):
    def _add(product_id: int, quantity: int = 1, headers: dict | None = None):
        response = client.post(
            "/cart/items",
            json={"product_id": product_id, "quantity": quantity},
            headers=headers or {},
        )
        return response

    return _add


@pytest.fixture
def place_order(client):
    def _place(shipping_address_id: int, billing_address_id: int, headers: dict):
        response = client.post(
            "/order",
            json={
                "shipping_address_id": shipping_address_id,
                "billing_address_id": billing_address_id,
            },
            headers=headers,
        )
        return response

    return _place


@pytest.fixture
def user_token(register_user, login_user):
    payload, register_response = register_user()
    assert register_response.status_code == 200
    login_response = login_user(payload["email"], payload["password"])
    assert login_response.status_code == 200
    return login_response.json()["token"]


@pytest.fixture
def admin_token(register_user, login_user, promote_user_to_admin):
    payload, register_response = register_user(first_name="Admin", last_name="User")
    assert register_response.status_code == 200
    promote_user_to_admin(payload["email"])
    login_response = login_user(payload["email"], payload["password"])
    assert login_response.status_code == 200
    return login_response.json()["token"]


@pytest.fixture
def order_factory(
    client,
    auth_headers,
    register_user,
    login_user,
    create_address_for_user,
    create_product_in_db,
    add_item_to_cart,
    place_order,
):
    def _factory(
        *,
        email: str | None = None,
        stock_quantity: int = 10,
        cart_quantity: int = 1,
        product_price: float = 50.0,
    ):
        payload, register_response = register_user(email=email)
        assert register_response.status_code == 200
        login_response = login_user(payload["email"], payload["password"])
        assert login_response.status_code == 200
        headers = auth_headers(login_response.json()["token"])

        _, address_response = create_address_for_user(headers)
        assert address_response.status_code == 200
        address_id = address_response.json()["id"]

        product = create_product_in_db(
            stock_quantity=stock_quantity,
            price=product_price,
        )
        cart_response = add_item_to_cart(
            product_id=product.id,
            quantity=cart_quantity,
            headers=headers,
        )
        assert cart_response.status_code == 200

        order_response = place_order(address_id, address_id, headers)
        return {
            "payload": payload,
            "headers": headers,
            "address_id": address_id,
            "product": product,
            "cart_response": cart_response,
            "order_response": order_response,
        }

    return _factory

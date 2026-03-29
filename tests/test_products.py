from sqlalchemy import select

from app.models.product import Product


def test_create_product_as_admin(client, db_session, admin_token, admin_headers, product_payload):
    payload = product_payload(name="Admin Product")
    response = client.post("/product", json=payload, headers=admin_headers(admin_token))
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["price"] == payload["price"]

    db_product = db_session.get(Product, data["id"])
    assert db_product is not None
    assert db_product.name == payload["name"]


def test_get_products(client, create_product_in_db):
    create_product_in_db(name="Phone Alpha")
    create_product_in_db(name="Phone Beta")

    response = client.get("/product")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "data" in data
    assert "meta" in data
    assert isinstance(data["data"], list)
    assert data["meta"]["current_page"] == 1
    assert data["meta"]["per_page"] == 10
    assert data["meta"]["total_items"] >= 2


def test_normal_user_cannot_create_product(client, user_token, auth_headers, product_payload):
    response = client.post(
        "/product",
        json=product_payload(name="Blocked Product"),
        headers=auth_headers(user_token),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin privileges required"


def test_get_product_by_slug_success(client, create_product_in_db):
    product = create_product_in_db(name="Slug Product", slug="slug-product")
    response = client.get(f"/product/{product.slug}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == product.id
    assert data["slug"] == product.slug


def test_update_product_as_admin_success(client, db_session, admin_token, admin_headers):
    create_response = client.post(
        "/product",
        json={
            "name": "Original Product",
            "description": "before update",
            "price": 20.0,
            "stock_quantity": 5,
            "image_url": "https://example.com/original.jpg",
        },
        headers=admin_headers(admin_token),
    )
    assert create_response.status_code == 201
    product_id = create_response.json()["id"]

    update_response = client.put(
        f"/product/{product_id}",
        json={"price": 30.5, "stock_quantity": 12, "description": "after update"},
        headers=admin_headers(admin_token),
    )
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["price"] == 30.5
    assert data["stock_quantity"] == 12
    assert data["description"] == "after update"

    db_product = db_session.get(Product, product_id)
    assert float(db_product.price) == 30.5
    assert db_product.stock_quantity == 12
    assert db_product.description == "after update"


def test_delete_product_as_admin_success(client, db_session, admin_token, admin_headers, create_product_in_db):
    product = create_product_in_db(name="Delete Product")

    delete_response = client.delete(
        f"/product/{product.id}", headers=admin_headers(admin_token)
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["detail"] == "product deleted successfully"

    assert db_session.get(Product, product.id) is None
    get_response = client.get(f"/product/{product.slug}")
    assert get_response.status_code == 404

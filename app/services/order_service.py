from fastapi import HTTPException, status

from app.core.exceptions import OrderException
from app.crud.order import OrderCrud


class OrderService:
    def __init__(self, db):
        self.crud = OrderCrud(db)

    def place_order(self, user_id: int, shipping_id: int, billing_id: int):
        try:
            return self.crud.create_order(user_id, shipping_id, billing_id)
        except OrderException as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

    def list_orders(self, user_id: int):
        return self.crud.get_orders(user_id)

    def get_one_order(self, user_id: int, order_id: int):
        try:
            return self.crud.get_order_by_id(user_id, order_id)
        except OrderException as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

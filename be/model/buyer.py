import uuid
import json
import logging
from datetime import timedelta
from be.db_conn import *
from be.model import error
from threading import Timer


class Buyer():
    def new_order(self, user_id: str, store_id: str, id_and_count: [(str, int)]) -> (int, str, str):
        order_id = ""
        if not user_id_exist(user_id):
            return error.error_non_exist_user_id(user_id) + (order_id,)
        if not store_id_exist(store_id):
            return error.error_non_exist_store_id(store_id) + (order_id,)
        uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))

        for book_id, count in id_and_count:
            store_detail = session.query(Store_detail).filter(Store_detail.store_id == store_id,
                                                              Store_detail.book_id == book_id).first()
            if (store_detail is None):
                return error.error_non_exist_book_id(book_id) + (order_id,)

            stock_level = store_detail.stock_level

            if stock_level < count:
                return error.error_stock_level_low(book_id) + (order_id,)

            store_detail.stock_level -= count
            session.add(Order_detail(order_id=uid, book_id=book_id, count=count))
        session.add(Order_to_Pay(order_id=uid, user_id=user_id, store_id=store_id, paytime=datetime.now()))
        session.commit()
        order_id = uid
        return 200, "ok", order_id

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        order2pay = session.query(Order_to_Pay).filter(Order_to_Pay.order_id == order_id).first()

        if order2pay is None:
            return error.error_invalid_order_id(order_id)

        buyer_id = order2pay.user_id
        store_id = order2pay.store_id

        if buyer_id != user_id:
            return error.error_authorization_fail()

        buyer = session.query(User).filter(User.user_id == buyer_id).first()
        if buyer is None:
            return error.error_non_exist_user_id(buyer_id)
        balance = buyer.balance
        if (password != buyer.password):
            return error.error_authorization_fail()

        store = session.query(Store).filter(Store.store_id == store_id).first()
        if store is None:
            return error.error_non_exist_store_id(store_id)

        seller_id = store.user_id
        if not user_id_exist(seller_id):
            return error.error_non_exist_user_id(seller_id)

        order_detail = session.query(Order_detail).filter(Order_detail.order_id == order_id).all()
        total_price = 0
        for i in range(0, len(order_detail)):
            book_id = order_detail[i].book_id
            book = session.query(Store_detail).filter(Store_detail.store_id == store_id,
                                                      Store_detail.book_id == book_id).first()
            count = order_detail[i].count
            price = book.price
            total_price = total_price + price * count

        if balance < total_price:
            return error.error_not_sufficient_funds(order_id)

        buyer.balance -= total_price
        seller = session.query(User).filter(User.user_id == seller_id).first()
        seller.balance += total_price

        session.add(Order(order_id=order_id, user_id=buyer_id, store_id=store_id, paytime=datetime.now(), status=0))
        session.delete(order2pay)
        session.commit()
        return 200, "ok"

    def add_funds(self, user_id, password, add_value) -> (int, str):
        user = session.query(User).filter(User.user_id == user_id).first()
        if user is None:
            return error.error_authorization_fail()

        if user.password != password:
            return error.error_authorization_fail()

        user.balance += add_value
        session.commit()
        return 200, "ok"
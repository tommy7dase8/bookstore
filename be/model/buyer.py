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

    def receive_books(self, buyer_id, order_id):
        order = session.query(Order).filter(Order.order_id == order_id).first()
        if order is None:
            return error.error_invalid_order_id(order_id)
        if order.status == 0:
            return error.error_order_unsent(order_id)
        if order.status == 2:
            return error.error_order_received(order_id)
        if order.user_id != buyer_id:
            return error.error_authorization_fail()
        order.status = 2
        session.commit()
        return 200, "ok"

    def check_order(self):
        # 自动取消：检查未付款order是否超出15min
        order2pay = session.query(Order_to_Pay).all()
        if order2pay is not []:
            for i in range(len(order2pay)):
                paytime = order2pay[i].paytime
                time_now = datetime.now()
                old_time = datetime.strptime(str(paytime), "%Y-%m-%d %H:%M:%S.%f")
                new_time = datetime.strptime(str(time_now), "%Y-%m-%d %H:%M:%S.%f")
                time_lag = (new_time - old_time).seconds

                if (time_lag > 15 * 60):
                    order_id = order2pay[i].order_id
                    user_id = order2pay[i].user_id
                    store_id = order2pay[i].store_id

                    # 商品退回
                    store = session.query(Store).filter(Store.store_id == store_id).first()
                    if store is None:
                        return error.error_non_exist_store_id(store_id)
                    order_detail = session.query(Order_detail).filter(Order_detail.order_id == order_id).all()
                    total_price = 0
                    for i in range(len(order_detail)):
                        book_id = order_detail[i].book_id
                        book = session.query(Store_detail).filter(Store_detail.store_id == store_id,
                                                                  Store_detail.book_id == book_id).first()
                        count = order_detail[i].count
                        price = book.price
                        total_price += price * count
                        book.stock_level += count

                    session.add(Order(order_id=order_id, user_id=user_id, store_id=store_id, paytime=paytime, status=4))
                    session.delete(order2pay[i])
                    session.commit()
                    return 200, "ok", "closed"
        return 200, "ok", None

    def close_order(self, user_id: str, password: str, order_id: str) -> (int, str):
        # 手动取消
        order = session.query(Order).filter(Order.order_id == order_id).first()
        order2pay = session.query(Order_to_Pay).filter(Order_to_Pay.order_id == order_id).first()

        if order is None and order2pay is None:
            return error.error_invalid_order_id(order_id)

        if (order is not None):
            # 已付款：加回库存，修改买家卖家状态
            status = order.status
            if status == 4:
                return error.error_order_closed(order_id)
            elif status == 1 or status == 2:
                return error.error_order_can_not_be_closed(order_id)

            buyer_id = order.user_id
            store_id = order.store_id
            flag = 0

        elif (order2pay is not None):
            # 未付款：加回库存
            buyer_id = order2pay.user_id
            store_id = order2pay.store_id
            flag = 3

        if buyer_id != user_id:
            return error.error_authorization_fail()

        buyer = session.query(User).filter(User.user_id == buyer_id).first()
        if buyer is None:
            return error.error_non_exist_user_id(buyer_id)
        if (password != buyer.password):
            return error.error_authorization_fail()

        store = session.query(Store).filter(Store.store_id == store_id).first()
        if store is None:
            return error.error_non_exist_store_id(store_id)

        order_detail = session.query(Order_detail).filter(Order_detail.order_id == order_id).all()
        total_price = 0
        for i in range(len(order_detail)):
            book_id = order_detail[i].book_id
            book = session.query(Store_detail).filter(Store_detail.store_id == store_id,
                                                      Store_detail.book_id == book_id).first()
            count = order_detail[i].count
            price = book.price
            total_price += price * count
            book.stock_level += count  # 取消商品,退回库存

        if (flag == 0):
            seller_id = store.user_id
            if not user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)
            seller = session.query(User).filter(User.user_id == seller_id).first()
            seller.balance -= total_price
            buyer.balance += total_price
            order.status = 4
        elif (flag == 3):
            paytime = order2pay.paytime
            session.add(Order(order_id=order_id, user_id=buyer_id, store_id=store_id, paytime=paytime, status=4))
            session.delete(order2pay)
        session.commit()
        return 200, "ok"

    def search_order(self, user_id: str, password: str) -> (int, str, list):
        user = session.query(User).filter(User.user_id == user_id).first()
        if user is None:
            return 401, "authorization fail.", []

        if user.password != password:
            return 401, "authorization fail.", []

        historys = []

        # 未付款 因为在单独的表里面
        order2pay = session.query(Order_to_Pay).all()
        if (order2pay != []):
            for i in range(len(order2pay)):
                order_id = order2pay[i].order_id
                status = "未付款"
                order_detail = session.query(Order_detail).filter(Order_detail.order_id == order_id).all()
                details = []
                total_price = 0
                for j in range(len(order_detail)):
                    book = session.query(Store_detail).filter(Store_detail.store_id == order2pay[i].store_id,
                                                              Store_detail.book_id == order_detail[j].book_id).first()
                    price = book.price
                    total_price += price * order_detail[j].count
                    detail = {"book_id": order_detail[j].book_id, "count": order_detail[j].count, "single_price": price}
                    details.append(detail)
                history = {"order_id": order_id, "user_id": order2pay[i].user_id, "store_id": order2pay[i].store_id,
                           "total_price": total_price, "order_detail": details, "paytime": order2pay[i].paytime,
                           "status": status}
                historys.append(history)

        # 其它状态
        order = session.query(Order).order_by(Order.paytime).all()
        if (order != []):
            for i in range(len(order)):
                order_id = order[i].order_id
                status = order[i].status
                if (status == 0):
                    status = "已付款，待发货"
                elif (status == 1):
                    status = "已发货"
                elif (status == 2):
                    status = "已收货"
                elif (status == 4):
                    status = "交易关闭"

                order_detail = session.query(Order_detail).filter(Order_detail.order_id == order_id).all()
                details = []
                total_price = 0
                for j in range(len(order_detail)):
                    book = session.query(Store_detail).filter(Store_detail.store_id == order[i].store_id,
                                                              Store_detail.book_id == order_detail[j].book_id).first()
                    price = book.price
                    total_price += price * order_detail[j].count
                    detail = {"book_id": order_detail[j].book_id, "count": order_detail[j].count, "single_price": price}
                    details.append(detail)
                history = {"order_id": order_id, "user_id": order[i].user_id, "store_id": order[i].store_id,
                           "total_price": total_price, "order_detail": details, "paytime": order[i].paytime,
                           "status": status}
                historys.append(history)

        if (len(historys) != 0):
            return 200, "ok", historys
        else:
            return 200, "ok", historys


def auto_run():
    t = Timer(1.0, Buyer.check_order())  # 每秒调用1次
    t.start()
    t.cancel()

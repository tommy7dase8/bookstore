import uuid

import jwt
import logging
import time
import sqlalchemy
from be.model import error
from be.db_conn import *


# encode a json string like:
#   {
#       "user_id": [user name],
#       "terminal": [terminal code],
#       "timestamp": [ts]} to a JWT
#   }


def jwt_encode(user_id: str, terminal: str) -> str:
    encoded = jwt.encode(
        {"user_id": user_id, "terminal": terminal},
        key=user_id,
        algorithm="HS256",
    )
    return encoded


# decode a JWT to a json string like:
#   {
#       "user_id": [user name],
#       "terminal": [terminal code],
#       "timestamp": [ts]} to a JWT
#   }
def jwt_decode(encoded_token, user_id: str) -> str:
    decoded = jwt.decode(encoded_token, key=user_id, algorithms="HS256")
    return decoded


class Player():
    token_lifetime: int = 3600  # 3600 second

    def register(self, user_id: str, password: str):
        terminal = "terminal_{}".format(str(uuid.uuid1()))
        token = jwt_encode(user_id, terminal)
        cursor = session.query(User).filter(User.user_id == user_id).first()
        if cursor is not None:
            return error.error_exist_user_id(user_id)
        user_one = User(
            user_id=user_id,
            password=password,
            balance=0,
            token=token,
            terminal=terminal
        )
        session.add(user_one)
        session.commit()
        return 200, "ok"

    def check_token(self, user_id: str, token: str) -> (int, str):
        cursor = session.query(User).filter(User.user_id == user_id).first()
        if cursor is None:
            return error.error_authorization_fail()
        db_token = cursor.token
        # print('sss')
        hex_str = r"\x" + bytes(token, encoding='utf-8').hex()
        if db_token != token and db_token != hex_str:
            return error.error_authorization_fail()
        return 200, "ok"

    def check_password(self, user_id: str, password: str) -> (int, str):
        user_one = session.query(User).filter(User.user_id == user_id).first()
        if user_one is None:
            return error.error_authorization_fail()

        if password != user_one.password:
            return error.error_authorization_fail()

        return 200, "ok"

    def login(self, user_id: str, password: str, terminal: str) -> (int, str, str):
        token = ""
        code, message = self.check_password(user_id, password)
        if code != 200:
            return code, message, ""
        token = jwt_encode(user_id, terminal)
        cursor = session.query(User).filter(User.user_id == user_id).first()
        cursor.token = token
        cursor.terminal = terminal
        session.commit()
        return 200, "ok", token

    def logout(self, user_id: str, token: str) -> bool:
        code, message = self.check_token(user_id, token)
        if code != 200:
            return code, message

        terminal = "terminal_{}".format(str(uuid.uuid1()))
        dummy_token = jwt_encode(user_id, terminal)
        cursor = session.query(User).filter(User.user_id == user_id).first()
        cursor.token = dummy_token
        cursor.terminal = terminal
        session.commit()
        return 200, "ok"

    def unregister(self, user_id: str, password: str) -> (int, str):
        code, message = self.check_password(user_id, password)
        if code != 200:
            return code, message
        cursor = session.query(User).filter(User.user_id == user_id).first()
        session.delete(cursor)
        session.commit()
        return 200, "ok"

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        code, message = self.check_password(user_id, old_password)
        if code != 200:
            return code, message

        terminal = "terminal_{}".format(str(uuid.uuid1()))
        token = jwt_encode(user_id, terminal)
        cursor = session.query(User).filter(User.user_id == user_id).first()
        cursor.password = new_password
        cursor.token = token
        cursor.terminal = terminal
        session.commit()
        return 200, "ok"
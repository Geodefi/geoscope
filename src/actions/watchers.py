# -*- coding: utf-8 -*-
import requests
from src.helpers.gnosis import get_nonce, prepare_tx
from src.globals import get_sdk


def post_submit(method_id, types, values):
    # todo: error handling here.
    target = get_sdk().portal.address
    safe_nonce = get_nonce()
    tx = prepare_tx(safe_nonce, target, method_id, types, values)
    data = {"nonce": safe_nonce, "transaction": tx, "merkles": []}
    res = requests.post(url="http://localhost:3000/v1/submit", json=data, timeout=20)
    # print(res, res.text)

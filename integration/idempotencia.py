# integration/idempotencia.py
import json
import os
import threading

lock = threading.Lock()
path = "procesadas.json"

def verificar_idempotencia(order_id):
    with lock:
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump([], f)

        with open(path, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []

        if order_id in data:
            return False

        data.append(order_id)

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        return True
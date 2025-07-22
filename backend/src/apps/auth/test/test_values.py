import uuid
from app.domain.values import Payload


def test_values_to_dict():
    sub_uuid = str(uuid.uuid4())
    pay = Payload(sub=sub_uuid, add_exp= 500)
    assert  pay.to_dict() and not pay.is_expired()
import service.database as db

from service.permissions import require_auth
from service.serializers import notification_to_dict
from service.utils import (
    build_json_response,
    send_response,
)


def handle_get_notifications(client_socket, current_user):
    if not require_auth(client_socket, current_user):
        return

    notifications = db.get_notifications(current_user["id"])

    payload = {
        "status": "success",
        "notifications": [
            notification_to_dict(notification)
            for notification in notifications
        ],
    }

    send_response(client_socket, build_json_response(200, "OK", payload))
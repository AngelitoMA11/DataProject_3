import json
import os
from datetime import datetime
from google.cloud import pubsub_v1

# Configura tu ID de proyecto y la suscripción
project_id = "dataproject3-458310"
subscription_id = "vuelos-sub"

output_folder = os.path.dirname(os.path.abspath(__file__))
os.makedirs(output_folder, exist_ok=True)

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

# Leer solo un mensaje cuando se ejecute
def pull_mensaje():
    response = subscriber.pull(
        request={
            "subscription": subscription_path,
            "max_messages": 1,
        },
        timeout=10
    )

    ack_ids = []
    for received_message in response.received_messages:
        try:
            data = json.loads(received_message.message.data.decode("utf-8"))
            timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")
            filename = os.path.join(output_folder, f"mensaje_{timestamp}.json")
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            print(f"Mensaje guardado en {filename}")
            ack_ids.append(received_message.ack_id)
        except json.JSONDecodeError as e:
            print("Error decodificando JSON:", e)

    if ack_ids:
        subscriber.acknowledge(request={"subscription": subscription_path, "ack_ids": ack_ids})

if __name__ == "__main__":
    pull_mensaje()
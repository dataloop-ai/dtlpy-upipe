import google
from google.api_core import retry
from google.cloud import pubsub_v1
from concurrent import futures

from requests import options
import json


class DataFrame:
    next_id = 0

    @staticmethod
    def from_val(val):
        return DataFrame(str(val).encode('utf-8'))

    def __init__(self, data=''.encode('utf-8')):
        self.data = data
        self.id = self.next_id
        self.next_id += 1


class Queue:
    def __init__(self, topic_id: str):
        self.topic_id = topic_id

    def enqueue(self, data) -> int:
        raise NotImplementedError("Q must implement frame enqueue")

    def dequeue(self):
        raise NotImplementedError("Q must implement frame dequeue")


class GCPQueue(Queue):
    project_id = 'viewo-g'

    def __init__(self, topic_id: str):
        super().__init__(topic_id)
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()
        self.topic_path = self.publisher.topic_path(self.project_id, topic_id)
        self.topic = None
        self.subscription = None
        self.subscription_id = "your-subscription-id"
        self.project_path = f"projects/{self.project_id}"
        self.init_topic()
        self.init_subscription()
        print("GCP Queue created")

    def init_topic(self):
        print("topic init")
        self.topic = self.get_topic_by_name(self.topic_path)
        if not self.topic:
            print(f"Topic doesnt exist, Creating topic: {self.topic_path}")
            self.topic = self.publisher.create_topic(request={"name": self.topic_path})
        else:
            print(f"Using existing topic: {self.topic_path}")

    def init_subscription(self):
        print("subscription init")
        if not self.subscription:
            self.subscription = self.create_subscription()

    def get_topics(self):
        topics = []
        project_path = f"projects/{self.project_id}"
        for topic in self.publisher.list_topics(request={"project": project_path}):
            topics.append(topic)
        return topics

    def get_topic_by_name(self, name: str):
        topics = self.get_topics()
        for topic in topics:
            if topic.name == name:
                return topic
        return None

    def enqueue(self, frame: dict):
        obj = json.dumps(frame)
        future = self.publisher.publish(self.topic_path, obj.encode('utf-8'))
        futures.wait([future], return_when=futures.ALL_COMPLETED)

    def dequeue(self, count=1):
        from concurrent.futures import TimeoutError
        timeout = 5.0

        subscription_path = self.subscriber.subscription_path(self.project_id, self.subscription_id)

        # The subscriber pulls a specific number of messages. The actual
        # number of messages pulled may be smaller than max_messages.
        response = self.subscriber.pull(
            request={"subscription": subscription_path, "max_messages": count},
            retry=retry.Retry(deadline=300),
        )
        frames = []
        ack_ids = []
        for received_message in response.received_messages:
            print(f"Received: {received_message.message.data}.")
            ack_ids.append(received_message.ack_id)
            json_str = received_message.message.data.decode('utf-8')
            frames.append(json.loads(json_str))

        # Acknowledges the received messages so they will not be sent again.
        self.subscriber.acknowledge(
            request={"subscription": subscription_path, "ack_ids": ack_ids}
        )

        print(
            f"Received and acknowledged {len(response.received_messages)} messages from {subscription_path}."
        )
        if count == 1:
            return frames[0]
        return frames

    def create_subscription(self):
        subscriber = pubsub_v1.SubscriberClient()
        subscription_path = subscriber.subscription_path(self.project_id, self.subscription_id)
        expiration_policy = pubsub_v1.types.ExpirationPolicy(ttl={"seconds": 60 * 60 * 24})
        # Wrap the subscriber in a 'with' block to automatically call close() to
        # close the underlying gRPC channel when done.
        with subscriber:
            try:
                new_subscription = subscriber.create_subscription(
                    request={"name": subscription_path, "topic": self.topic_path,
                             "expiration_policy": expiration_policy}
                )
                print(f"Subscription created: {new_subscription}")
            except google.api_core.exceptions.AlreadyExists:
                print(f"Getting existing subscription:{subscription_path}")
                for subscription in subscriber.list_subscriptions(
                        request={"project": self.project_path}
                ):
                    if subscription.name == subscription_path:
                        new_subscription = subscription
                        break
        return new_subscription

from upipe.types import cloud_q

if __name__ == "__main__":
    print("hi")
    q = cloud_q.GCPQueue("your-topic-id")
    for i in range(10):
        val = {"counter": i}
        q.enqueue(val)
        val = q.dequeue()
        if val["counter"] != i:
            raise ValueError("Queue mismatch")
        print(f"dequeued:{val}")

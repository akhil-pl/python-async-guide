from locust import HttpUser, task, between

class User(HttpUser):
    wait_time = between(1, 2)

    @task
    def get_data(self):
        self.client.get("/data")

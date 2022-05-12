class ProgressVisor:
    def __init__(self, message: str = 'Progress:'):
        self.message = message
        self.total_iterations = 0
        self.counter = 0

    @property
    def total(self):
        return self.total_iterations

    @total.setter
    def total(self, total_iterations):
        self.total_iterations = total_iterations

    def update(self):
        self.counter += 1

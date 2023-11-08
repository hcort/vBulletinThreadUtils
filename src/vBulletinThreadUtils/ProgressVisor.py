"""
    Interface to show the progress of a long job
"""


class ProgressVisor:
    """
        Basic progress visor.
        It only stores progress info, but does not display anything
    """
    def __init__(self, message: str = 'Progress:'):
        self.message = message
        self.total_iterations = 0
        self.counter = 0

    @property
    def total(self):
        return self.total_iterations

    @total.setter
    def total(self, total_iterations: int):
        self.total_iterations = total_iterations

    def update(self, n: int = 1):
        self.counter += n

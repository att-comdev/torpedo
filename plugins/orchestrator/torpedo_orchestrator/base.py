from abc import ABC, abstractmethod


class Base(ABC):

    @abstractmethod
    def get(self, **kwargs):
        pass

    @abstractmethod
    def post(self, **kwargs):
        pass

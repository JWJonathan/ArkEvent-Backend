from abc import ABC, abstractmethod

class BasePaymentProvider(ABC):
    @abstractmethod
    def create_payment_session(self, order):
        pass

    @abstractmethod
    def verify_webhook(self, request):
        pass

    @abstractmethod
    def handle_webhook(self, payload):
        pass

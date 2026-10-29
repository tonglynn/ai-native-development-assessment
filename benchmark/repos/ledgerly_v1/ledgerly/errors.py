class BillingError(Exception):
    """Raised for any invalid billing operation.

    ``code`` is a short machine-readable reason such as ``"negative_amount"``;
    ``message`` is optional human-readable detail.
    """

    def __init__(self, code: str, message: str = ""):
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code
        self.message = message

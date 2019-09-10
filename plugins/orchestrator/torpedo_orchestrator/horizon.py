from generic_client import GenericClient


class Horizon():

    def __init__(self, tc, auth, **kwargs):
        self.extra_args = kwargs.get("extra_args", None)
        self.tc = tc

    def get(self):
        gc = GenericClient({})
        tc_status, message = gc.GET(self.extra_args['url'], headers=None)
        return tc_status, message, self.tc

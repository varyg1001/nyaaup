from .utils import Config

class Auth():
    def __init__(self, args, parser):

        self.args = args
        self.parser = parser

        if self.args.add_credential:
            Config().add(self.args.add_credential)

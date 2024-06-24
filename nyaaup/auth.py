from .utils import Config


class Auth:
    def __init__(self, args, parser):
        self.args = args
        self.parser = parser

        config = Config()

        if self.args.add_credential:
            config.add(self.args.add_credential)

from .utils.config import Config


class Auth:
    def __init__(self, args, parser):
        self.args = args
        self.parser = parser

        config = Config()

        if self.args.add_credentifal:
            config.add(self.args.add_credential)

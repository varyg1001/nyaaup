from .utils import Config, wprint, eprint


class Auth:
    def __init__(self, args, parser):
        self.args = args
        self.parser = parser

        conf = Config()
        config = conf.load(False)

        def_an = "http://nyaa.tracker.wf:7777/announce"
        provider = None
        name = self.args.provider or "nyaasi"
        api = self.args.api or "https://nyaa.si/api/v2/upload"
        announces = [self.args.announces] if self.args.announces else []
        credential = self.args.credential
        
        if not self.args.announces and not self.args.api and not self.args.credential:
            eprint("No arguments provided!", True)

        if credential:
            conf.get_cred(credential)

        if providers := config.get("providers"):
            for x in providers:
                if x.get("name") == name:
                    provider = x
                    break
        else:
            if not credential:
                eprint(
                    "Could not find specified provider and no credential provided!",
                    True,
                )
            config["providers"] = []

        if not provider:
            wprint("Could not find specified provider in the config!")

            if def_an not in announces:
                announces.append("http://nyaa.tracker.wf:7777/announce")

            config["providers"].append(
                {
                    "name": name,
                    "api": api,
                    "credentials": credential,
                    "announces": announces,
                }
            )
        else:
            if announces:
                provider["announces"] += announces
            if api:
                provider["api"] = api
            if credential:
                provider["credentials"] = credential

        conf.update(config)

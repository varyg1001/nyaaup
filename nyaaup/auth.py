from .utils import Config, eprint, wprint


class Auth:
    def __init__(self, args, parser):
        self.args = args
        self.parser = parser

        conf = Config()
        config = conf.load(False)

        def_an = "http://nyaa.tracker.wf:7777/announce"
        provider = None
        name = self.args.provider or "nyaasi"
        domain = self.args.domain or "https://nyaa.si"
        proxy = self.args.proxy or None
        announces = [self.args.announces] if self.args.announces else []
        credential = self.args.credential

        if not self.args.announces and not self.args.domain and not self.args.credential:
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
                    "domain": domain,
                    "credentials": credential,
                    "proxy": proxy,
                    "announces": announces,
                }
            )
        else:
            if announces:
                provider["announces"] += announces
            if domain:
                provider["domain"] = domain
            if credential:
                provider["credentials"] = credential
            if proxy:
                provider["proxy"] = proxy

        conf.update(config)

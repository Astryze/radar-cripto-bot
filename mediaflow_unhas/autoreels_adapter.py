# ruff: noqa
"""Cliente opcional da API pública documentada do AutoReels, sem copiar código upstream.
Não garante vídeos de dez imagens / dez segundos: use o renderer MediaFlow para isso.
"""
import ipaddress
from urllib.parse import urlsplit
import requests

class AutoReelsClient:
    def __init__(self, base="http://127.0.0.1:8420", session=None):
        u=urlsplit(base)
        try: local=ipaddress.ip_address(u.hostname or "").is_loopback
        except ValueError: local=u.hostname=="localhost"
        if u.scheme!="http" or not local or u.username or u.password or u.query or u.fragment or u.path not in ("","/"):
            raise ValueError("AutoReels deve rodar em servidor HTTP local")
        self.base=base.rstrip("/")
        self.session=session or requests.Session()
    def health(self):
        r=self.session.get(self.base+"/api/health",timeout=10);r.raise_for_status();return r.json()
    def trigger(self,topic):
        if not topic or len(topic)>140:raise ValueError("Tema inválido")
        r=self.session.post(self.base+"/api/trigger",json={"topic":topic},timeout=15)
        r.raise_for_status();return r.json()

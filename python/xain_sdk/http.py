# pylint: disable=missing-docstring,invalid-name
import json
import urllib
import requests

from logzero import logger as LOG


def log_headers(headers):
    for (name, value) in headers.items():
        LOG.debug("%s: %s", name, value)


def log_request(req):
    LOG.info(">>> %s %s", req.method, req.url)
    log_headers(req.headers)
    content_type = req.headers.get('content-type')
    if content_type == 'application/json':
        parsed = json.loads(req.body.decode("utf-8"))
        LOG.info(json.dumps(parsed, indent=4))


def log_response(resp):
    if resp.status_code >= 200 and resp.status_code < 300:
        logger = LOG.info
    else:
        logger = LOG.warning
    logger("<<< %s %s [%s]", resp.request.method, resp.request.url, resp.status_code)
    log_headers(resp.headers)
    content_type = resp.headers.get('content-type')
    if content_type == 'application/json':
        parsed = json.loads(resp.text)
        LOG.info(json.dumps(parsed, indent=4))

class HttpClient:
    def __init__(self, url):
        if isinstance(url, urllib.parse.ParseResult):
            self._url = url
        else:
            self._url = urllib.parse.urlparse(url)
        assert self._url.scheme

    def url(self, path):
        path = path.strip("/")
        return f"{self._url.scheme}://{self._url.netloc}/{path}"

    def delete(self, path, status=204, **kwargs):
        req = self.build_req("DELETE", path, **kwargs)
        return self.send(req, status=status)

    def patch(self, path, status=200, **kwargs):
        req = self.build_req("PATCH", path, **kwargs)
        return self.send(req, status=status)

    def post(self, path, status=200, **kwargs):
        req = self.build_req("POST", path, **kwargs)
        return self.send(req, status=status)

    def put(self, path, status=200, **kwargs):
        req = self.build_req("PUT", path, **kwargs)
        return self.send(req, status=status)

    def get(self, path, status=200, **kwargs):
        req = self.build_req("GET", path, **kwargs)
        return self.send(req, status=status)

    @staticmethod
    def headers():
        headers = {}
        return headers

    def build_req(self, method, path, **kwargs):
        kwargs["headers"] = dict(kwargs.get("headers", {}), **self.headers())
        return requests.Request(method.upper(), self.url(path), **kwargs)

    def send(self, req, status=200):
        prepared = req.prepare()
        log_request(prepared)
        resp = requests.Session().send(prepared)
        log_response(resp)
        self.check_response(resp, status=status)
        return resp

    @staticmethod
    def check_response(resp, status=200):
        if not resp.status_code == status:
            raise ApiError(resp)


class ApiError(Exception):
    def __init__(self, response, *args, **kwargs):
        self.response = response
        self.error = response.text
        super().__init__(self.error, *args, **kwargs)


class CoordinatorClient:
    def __init__(self, url):
        self.http = HttpClient(url)

    def heartbeat(self, id):
        return json.loads(self.http.get(f"heartbeat/{id}").text)

    def rendez_vous(self):
        return json.loads(self.http.get("rendez_vous").text)


class AggregatorClient:
    def __init__(self, url):
        self.http = HttpClient(url)

    def download(self, id, token):
        resp = self.http.get(f"{id}/{token}")
        return resp

    def upload(self, id, token, weights):
        resp = self.http.post(f"{id}/{token}", body=weights)
        return resp

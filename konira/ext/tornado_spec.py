import json
import urllib
from tornado.testing import AsyncTestCase, AsyncHTTPTestCase

class UnittestSpecBase(object):

    def runTest(self):
        """required by pyUnit init method"""

    def _before_all(self):
        self.before_all()

    def _after_all(self):
        self.after_all()

    def _before_each(self):
        self.before_each()

    def before_each(self):
        pass

    def _after_each(self):
        self.after_each()

    def after_each(self):
        pass

    def before_all(self):
        self.setUp()

    def after_all(self):
        self.tearDown()

class AsyncSpec(AsyncTestCase, UnittestSpecBase):
    pass

class AsyncHTTPSpec(AsyncHTTPTestCase, UnittestSpecBase):

    def fetch(self, path, **kwargs):
        """Convenience method to synchronously fetch a url.

        The given path will be appended to the local server's host and
        port.  Any additional kwargs will be passed directly to
        `.AsyncHTTPClient.fetch` (and so could be used to pass
        ``method="POST"``, ``body="..."``, etc).

        If ``data`` parameter passed instead of body then

        """
        if "body" not in kwargs:
            data = kwargs.pop("data", None)
            as_json = kwargs.pop("as_json", False)
            method = kwargs.get("method")
            headers = kwargs.get("headers", {})
            if method not in ("GET", "HEAD", "OPTIONS"):
                if isinstance(data, dict):
                    if as_json:
                        kwargs["body"] = json.dumps(data)
                        headers['Content-Type'] = "application/json"
                    else:
                        headers['Content-Type'] = "application/x-www-form-urlencoded"
                        kwargs["body"] = urllib.urlencode(data.items())
                elif data is not None:
                    kwargs["body"] = str(data)
            else:
                assert isinstance(data, dict)
                encoded_params = urllib.urlencode(data.items())
                if "?" not in path:
                    path += "?" + encoded_params
                else:
                    path += "&" + encoded_params
            if headers:
                kwargs["headers"] = dict(kwargs.get("headers", {}), **headers)
        return super(AsyncHTTPSpec, self).fetch(path, **kwargs)

    def parse_response_body(self, response):
        ctype = response.headers.get('Content-Type')
        if ctype and "json" in ctype:
            return json.loads(response.body)
        else:
            return response.body
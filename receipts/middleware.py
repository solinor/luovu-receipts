class NoCacheHeaders(object):  # pylint:disable=too-few-public-methods
    def process_response(self, request, response):
        response['Cache-Control'] = "no-cache, no-store, must-revalidate"
        response['Expires'] = "0"
        return response
import os
import sys
import time
import hotshot

class ProfileMiddleware(object):
    def process_request(self, request):
        filename = "%s.%s.prof" % (request.path.strip("/").replace('/', '.'),
                                   request.method.upper())
        self.filename = os.path.join('profile', filename)

        path = os.path.dirname(self.filename)
        if not os.path.isdir(path):
            os.makedirs(path)

        self.prof = hotshot.Profile(self.filename)
        self.start = time.time()

    def process_view(self, request, callback, args, kw):
        return self.prof.runcall(callback, request, *args, **kw)

    def process_response(self, request, response):
        print "-- Request finished:", request.path
        
        if self.start:
            print "-- Time:", time.time() - self.start
            self.start = None
        
        if self.prof:
            self.prof.close()
            print "-- Profile:", os.path.basename(self.filename)
        
        return response

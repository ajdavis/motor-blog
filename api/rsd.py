import tornado.web
import tornado.template

from text.link import absolute


class RSDHandler(tornado.web.RequestHandler):
    """MarsEdit uses RSD to determine the blog's XML-RPC capabilities. Link to
       this URL from your base template's <head>, e.g.:

       <link rel="EditURI" type="application/rsd+xml" title="RSD" href="/{{ reverse_url('rsd') }}" />

       http://en.wikipedia.org/wiki/Really_Simple_Discovery
    """
    def get(self):
        self.set_header('Content-Type', 'text/xml')
        t = tornado.template.Template(rsd_template)
        self.write(t.generate(
            reverse_url=self.reverse_url, absolute=absolute))


rsd_template = """<?xml version="1.0" encoding="UTF-8"?>
<rsd version="1.0" xmlns="http://archipelago.phrasewise.com/rsd">
    <service>
        <engineName>Motor-Blog</engineName>
        <engineLink>https://github.com/ajdavis/motor-blog/</engineLink>
        <homePageLink>{{ reverse_url('api') }}</homePageLink>
        <apis>
            <api name="WordPress" blogID="1" preferred="true"
                 apiLink="{{ absolute(reverse_url('api')) }}" />
        </apis>
    </service>
</rsd>"""
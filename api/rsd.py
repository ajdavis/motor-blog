import tornado.web

# TODO: comment
class RSDHandler(tornado.web.RequestHandler):
    def get(self):
        # TODO: use blog settings instead of hard coding
        self.write("""<?xml version="1.0" encoding="UTF-8"?><rsd version="1.0" xmlns="http://archipelago.phrasewise.com/rsd">
          <service>
            <engineName>Motor-Blog</engineName>
            <engineLink>TODO</engineLink>
            <homePageLink>http://localhost:8888/blog/</homePageLink> <!-- TODO -->
            <apis>
              <!-- TODO -->
              <api name="WordPress" blogID="1" preferred="true" apiLink="http://localhost:8888/blog/api" />
            </apis>
          </service>
        </rsd>
        """)

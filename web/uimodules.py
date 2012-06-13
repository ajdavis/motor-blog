import tornado.web

# TODO: remove, just subclass RequestHandler to add a 'settings' function to
# all templates' scope, as well as cached list of categories
class Setting(tornado.web.UIModule):
    """Get a value from application settings, perhaps ultimately from a
       command-line option or from motor_blog.conf"""
    def render(self, option_name):
        return self.handler.application.settings[option_name].value()

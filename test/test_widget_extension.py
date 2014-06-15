import unittest

from bs4 import BeautifulSoup

from motor_blog.text.markup import markup


_text = '''
start

!!widget option1 option2!!

end
'''


class WidgetTest(unittest.TestCase):
    def test_widget(self):
        html = markup(_text)
        soup = BeautifulSoup(html)
        widgets = soup.find_all('widget')
        self.assertEqual(1, len(widgets))
        self.assertEqual(
            'widget option1 option2',
            widgets[0].text)

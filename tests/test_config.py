import unittest

from tempfile import NamedTemporaryFile

from src.config import ConfigAdapter


class TestCaseConfig(unittest.TestCase):

    def setUp(self):
        config_test = """
        [DEFAULT]
        ServerAliveInterval = 45
        Compression = yes
        CompressionLevel = 9
        ForwardX11 = yes

        [bitbucket.org]
        User = hg

        [topsecret.server.com]
        Port = 50022
        ForwardX11 = no
        """
        self.fp = NamedTemporaryFile()
        self.fp.write(config_test.encode('utf-8'))
        self.fp.flush()

    def tearDown(self):
        self.fp.close()

    def test_config_adapter(self):
        config = ConfigAdapter(filename=self.fp.name)
        self.assertEqual(config['bitbucket.org']['User'], 'hg')
        self.assertCountEqual(
            config.sections(),
            ['topsecret.server.com', 'bitbucket.org']
        )
        self.assertTrue(
            config.getboolean('bitbucket.org', 'Compression')
        )
        self.assertEqual(
            config['topsecret.server.com'].get('CompressionLevel'),
            '9'
        )
        self.assertEqual(
            config['topsecret.server.com'].getint('CompressionLevel'),
            9
        )
        self.assertTrue('bitbucket.org' in config)

    def test_config_adapter_singleton(self):
        a_config = ConfigAdapter(filename=self.fp.name)
        a_same_config = ConfigAdapter(self.fp.name)
        self.assertEqual(a_config, a_same_config)

        config_test = """
        [test]
        foo = 45
        """
        with NamedTemporaryFile() as fp:
            fp.write(config_test.encode('utf-8'))
            fp.flush()
            b_config = ConfigAdapter(self.fp.name)
            c_config = ConfigAdapter(filename=fp.name)
            self.assertNotEqual(b_config, c_config)


if __name__ == '__main__':
    unittest.main()

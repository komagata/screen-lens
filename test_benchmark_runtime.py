import importlib.util
import unittest


class RuntimeTest(unittest.TestCase):
    def test_auto_fit_is_explicit_and_keeps_private_socket(self):
        self.assertIsNotNone(importlib.util.find_spec('benchmark_runtime'))
        from benchmark_runtime import command
        config = dict(server='/bin/server', model='/tmp/model', projector='/tmp/vision')
        argv = command(config, '/tmp/private.sock', 'auto', 1024)
        self.assertEqual(argv[argv.index('-ngl')+1], 'auto')
        self.assertEqual(argv[argv.index('--fit')+1], 'on')
        self.assertEqual(argv[argv.index('--host')+1], '/tmp/private.sock')
        self.assertIn('--offline', argv)
        with self.assertRaises(ValueError): command(config, '/tmp/private.sock', 'bad', 1024)

    def test_native_gemma_image_token_budget(self):
        from benchmark_runtime import command
        argv = command(dict(server='/bin/server', model='/tmp/model', projector='/tmp/vision', image_tokens=256), '/tmp/private.sock')
        self.assertEqual(argv[argv.index('--image-max-tokens')+1], '256')

    def test_gemma_compatibility_template_is_opt_in(self):
        from benchmark_runtime import command
        argv = command(dict(server='/bin/server', model='/tmp/model', compatible_gemma=True), '/tmp/private.sock')
        self.assertIn('--no-jinja', argv)
        self.assertEqual(argv[argv.index('--chat-template')+1], 'gemma')


if __name__ == '__main__': unittest.main()

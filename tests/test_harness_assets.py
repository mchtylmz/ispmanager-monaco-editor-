"""Exercise only the two development asset-serving branches, without sockets."""
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, str(PROJECT / 'tools' / (name + '.py')))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SERVERS = [load('editor_server'), load('preview_server')]


class HarnessAssetsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.anchor = Path(self.temp.name)
        self.root = self.anchor / 'project'
        self.assets = self.root / 'dist/frontend'
        (self.assets / 'chunks').mkdir(parents=True)
        (self.assets / 'app.js').write_bytes(b'NORMAL_JS')
        (self.assets / 'chunks/style.css').write_bytes(b'NORMAL_CSS')
        (self.assets / 'file.unknownextension').write_bytes(b'NORMAL_BINARY')
        self.outside = self.anchor / 'outside.txt'
        self.outside.write_bytes(b'OUTSIDE_SYNTHETIC_FIXTURE')

    def request(self, module, relative):
        handler = module.Handler.__new__(module.Handler)
        handler.path = module.preview.ASSETS + '/' + relative
        handler.wfile = io.BytesIO()
        state = {'status': None, 'headers': {}}
        handler.send_response = lambda status: state.update(status=status)
        handler.send_error = lambda status: state.update(status=status)
        handler.send_header = lambda key, value: state['headers'].update({key: value})
        handler.end_headers = lambda: None
        with patch.object(module, 'ROOT', self.root):
            handler.do_GET()
        state['body'] = handler.wfile.getvalue()
        return state

    def test_regular_nested_assets_query_and_mime_remain_available(self):
        for module in SERVERS:
            for relative, content, mime in [('app.js?v=1', b'NORMAL_JS', 'text/javascript'),
                                            ('chunks/style.css', b'NORMAL_CSS', 'text/css'),
                                            ('file.unknownextension', b'NORMAL_BINARY', 'application/octet-stream')]:
                with self.subTest(server=module.__name__, path=relative):
                    response = self.request(module, relative)
                    self.assertEqual(response['status'], 200)
                    self.assertEqual(response['body'], content)
                    self.assertEqual(response['headers']['Content-Type'], mime)

    def test_absolute_traversal_encoded_paths_missing_files_and_directories_refused(self):
        for module in SERVERS:
            paths = [self.outside.as_posix(), '../outside.txt', 'chunks/../../outside.txt',
                     '%2f' + self.outside.as_posix().lstrip('/').replace('/', '%2f'),
                     '%2e%2e/outside.txt', 'missing.js', 'chunks/']
            for relative in paths:
                with self.subTest(server=module.__name__, path=relative):
                    response = self.request(module, relative)
                    self.assertEqual(response['status'], 404)
                    self.assertEqual(response['body'], b'')

    def test_symlink_escape_and_loop_refused_inside_symlink_preserves_original_mime(self):
        (self.assets / 'escape.js').symlink_to(self.outside)
        (self.assets / 'escape-dir').symlink_to(self.anchor, target_is_directory=True)
        sibling = self.assets.parent / 'frontend-neighbor'
        sibling.mkdir(); (sibling / 'outside.txt').write_bytes(b'OUTSIDE_NEIGHBOR_FIXTURE')
        (self.assets / 'prefix-escape').symlink_to(sibling, target_is_directory=True)
        (self.assets / 'loop.js').symlink_to(self.assets / 'loop.js')
        (self.assets / 'inside.js').symlink_to(self.assets / 'chunks/style.css')
        for module in SERVERS:
            for relative in ('escape.js', 'escape-dir/outside.txt', 'prefix-escape/outside.txt', 'loop.js'):
                with self.subTest(server=module.__name__, path=relative):
                    response = self.request(module, relative)
                    self.assertEqual(response['status'], 404)
                    self.assertEqual(response['body'], b'')
            response = self.request(module, 'inside.js')
            self.assertEqual(response['status'], 200)
            self.assertEqual(response['body'], b'NORMAL_CSS')
            self.assertEqual(response['headers']['Content-Type'], 'text/javascript')

    def test_read_failure_returns_404(self):
        for module in SERVERS:
            with self.subTest(server=module.__name__), patch.object(Path, 'read_bytes', side_effect=PermissionError('synthetic')):
                response = self.request(module, 'app.js')
                self.assertEqual(response['status'], 404)
                self.assertEqual(response['body'], b'')


if __name__ == '__main__':
    unittest.main()

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import time
import unittest
from unittest.mock import patch


class LocalTranslationTests(unittest.TestCase):
    def test_model_process_dies_when_worker_is_killed(self):
        module = self.module()
        code = ('import os,subprocess,sys,time; p=subprocess.Popen([sys.executable,"-B",sys.argv[1],'
                '"--serve",str(os.getpid()),"/usr/bin/sleep","60"]); print(p.pid,flush=True); time.sleep(60)')
        parent = subprocess.Popen([sys.executable, '-c', code, module.__file__], stdout=subprocess.PIPE, text=True)
        child = int(parent.stdout.readline())
        def state():
            try: return Path(f'/proc/{child}/stat').read_text().split(') ', 1)[1].split()[0]
            except FileNotFoundError: return None
        try:
            deadline = time.monotonic()+3
            while Path(f'/proc/{child}/comm').read_text().strip() != 'sleep':
                if time.monotonic() > deadline: self.fail('Child did not exec')
                time.sleep(.02)
            parent.kill(); parent.wait(timeout=3)
            while state() not in (None, 'Z') and time.monotonic() < deadline: time.sleep(.02)
            self.assertIn(state(), (None, 'Z'))
        finally:
            if parent.poll() is None: parent.kill(); parent.wait()
            parent.stdout.close()
            if state() not in (None, 'Z'): os.kill(child, 9)

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('local_translation'))
        import local_translation
        return local_translation

    def test_image_and_nearby_context_with_strict_ids(self):
        from PIL import Image
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, SCREEN_LENS_SOURCE='en', SCREEN_LENS_TARGET='ja'):
            image = Path(tmp) / 'image.png'; Image.new('RGB', (800, 400)).save(image)
            row = dict(id='a', text='Open', x=20, y=30, width=80, height=20)
            neighbor = dict(row, id='b', text='Business hours', y=10)
            body = module.payload(dict(image=str(image), groups=[row], lines=[neighbor]), [row])
            content = body['messages'][1]['content']
            self.assertEqual(content[1]['type'], 'image_url')
            self.assertIn('Business hours', content[0]['text'])
            self.assertIn('Japanese', body['messages'][0]['content'])
            self.assertEqual(body['response_format']['json_schema']['schema']['required'], ['a'])

    def test_bad_identifiers_and_numbers_retain_source(self):
        module = self.module()
        rows = [dict(id='a', text='Contact @Adobe in 30 seconds'), dict(id='b', text='Save changes')]
        values, rejected = module.validate(rows, {'a': 'Adobeに3秒で連絡', 'b': '変更を保存'})
        self.assertEqual(values['a'], rows[0]['text'])
        self.assertEqual(values['b'], '変更を保存')
        self.assertEqual(rejected, ['a'])
        with self.assertRaises(ValueError): module.validate(rows, {'unexpected': 'bad'})
        original = 'Type demo and press Enter.'
        values, rejected = module.validate([dict(id='a', text=original)], {'a': 'デモタイプを入力'})
        self.assertEqual(values['a'], original)
        self.assertEqual(rejected, ['a'])

    def test_missing_local_configuration_never_uses_cloud(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, XDG_CONFIG_HOME=tmp):
            with self.assertRaisesRegex(ValueError, 'Local model'):
                module.configuration()

    def test_backend_changes_snapshot_cache(self):
        self.module()
        from PIL import Image
        from snapshot_cache import fingerprint
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / 'image.png'; Image.new('RGB', (5, 5)).save(image)
            with patch.dict(os.environ, SCREEN_LENS_PROVIDER='openai'):
                cloud = fingerprint(image, True)
            with patch.dict(os.environ, SCREEN_LENS_PROVIDER='local'), patch('local_translation.configuration', return_value={'model_id': 'test'}):
                self.assertNotEqual(cloud, fingerprint(image, True))

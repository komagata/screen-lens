import tempfile
from pathlib import Path
import unittest


class RuntimeBundleTests(unittest.TestCase):
    def test_shared_packages_are_omitted_only_when_requested(self):
        import runtime_bundle
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source';source.mkdir()
            for name in ('requests','requests-2.34.2.dist-info','numpy','numpy-2.5.3.dist-info','rapidocr'):
                (source/name).mkdir();(source/name/'keep').write_text('fixture')
            (source/'cv2.cpython-314-x86_64-linux-gnu.so').write_text('fixture')
            self.assertTrue(hasattr(runtime_bundle,'SHARED_BASE'))
            runtime_bundle.copy_runtime(source,Path(folder)/'base',shared='base')
            self.assertFalse((Path(folder)/'base/requests').exists())
            self.assertFalse((Path(folder)/'base/requests-2.34.2.dist-info').exists())
            self.assertTrue((Path(folder)/'base/numpy').exists())
            runtime_bundle.copy_runtime(source,Path(folder)/'extra',shared='extra')
            self.assertFalse((Path(folder)/'extra/numpy').exists())
            self.assertFalse((Path(folder)/'extra/numpy-2.5.3.dist-info').exists())
            self.assertFalse((Path(folder)/'extra/cv2.cpython-314-x86_64-linux-gnu.so').exists())
            self.assertTrue((Path(folder)/'extra/rapidocr').exists())
            runtime_bundle.copy_runtime(source,Path(folder)/'numpy-only',shared='numpy')
            self.assertFalse((Path(folder)/'numpy-only/numpy').exists())
            self.assertTrue((Path(folder)/'numpy-only/cv2.cpython-314-x86_64-linux-gnu.so').exists())

    def test_copy_preserves_runtime_and_licenses_but_omits_development_data(self):
        import runtime_bundle
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / 'source', Path(folder) / 'target'
            kept = ['numpy/__init__.py', 'numpy/testing/__init__.py',
                    'onnxruntime/LICENSE', 'onnxruntime/ThirdPartyNotices.txt',
                    'onnxruntime/capi/onnxruntime_inference_collection.py',
                    'numpy-2.5.3.dist-info/licenses/LICENSE.txt',
                    'rapidocr/models/PP-OCRv6_rec_small.onnx',
                    'rapidocr/models/ch_PP-OCRv5_det_mobile.onnx',
                    'rapidocr/models/ch_ppocr_mobile_v2.0_cls_mobile.onnx']
            omitted = ['numpy/tests/test_x.py', 'numpy/__pycache__/x.pyc',
                       'onnxruntime/transformers/optimizer.py',
                       'onnxruntime/quantization/quantize.py',
                       'onnxruntime/tools/convert_onnx_models_to_ort.py',
                       'rapidocr/models/PP-OCRv6_det_small.onnx',
                       'onnxruntime/capi/libonnxruntime.so.1.29.0']
            for name in kept + omitted:
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'fixture')
            self.assertTrue(callable(getattr(runtime_bundle, 'copy_runtime', None)),
                            'Runtime-only packaging is not implemented')
            runtime_bundle.copy_runtime(source, target)
            for name in kept:
                self.assertEqual((target / name).read_bytes(), b'fixture')
            for name in omitted:
                self.assertFalse((target / name).exists())
            self.assertTrue((source / omitted[0]).exists())
            with self.assertRaises(FileExistsError):
                runtime_bundle.copy_runtime(source, target)


if __name__ == '__main__':
    unittest.main()

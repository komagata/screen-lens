"""Optional isolated CPU detector bridge. No installation or downloads at runtime."""
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
EXPERIMENT=ROOT/'experiments/omniparser'


def detect_regions(path):
    required=[EXPERIMENT/'venv/bin/python',EXPERIMENT/'model.pt',
              EXPERIMENT/'source/util/yolov9.py']
    if not all(p.is_file() for p in required):
        raise RuntimeError('Optional OmniParser experiment environment is not installed')
    run=subprocess.run([str(required[0]),str(Path(__file__).resolve()),str(Path(path).resolve())],
                       capture_output=True,text=True,check=True,timeout=120)
    result=json.loads(run.stdout)
    result['warnings']=run.stderr
    return result


def main():
    import torch
    sys.path.insert(0,str(EXPERIMENT/'source'))
    from util.yolov9 import YOLOv9Detector
    torch.set_num_threads(4)
    model=YOLOv9Detector(EXPERIMENT/'model.pt',device='cpu')
    boxes=model.predict(sys.argv[1],conf=.05,imgsz=1280)[0].boxes
    print(json.dumps(dict(boxes=boxes.xyxy.tolist(),scores=boxes.conf.tolist(),
                         device='cpu',imgsz=1280,confidence=.05)))


if __name__=='__main__':main()

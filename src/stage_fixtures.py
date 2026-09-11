"""Invented, versioned inputs. Agent-authored truth, not human-reviewed corpus."""
import json
from PIL import Image, ImageDraw, ImageFont

FONT='/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc'
# Freeze before model calls. Evaluation cases are distinct texts, but remain
# synthetic and share drawing primitives: no claim of real-world generalization.
CASES=[
    ('backup','development',22,'#ffffff','#16202a','Release notes',
     ['The release is not ready yet.', 'Do not delete your backup.'],
     'リリースはまだ準備できていません。バックアップを削除しないでください。', ['削除しない'], []),
    ('store','development',24,'#17202b','#f0f2f5','営業時間',
     ['Open'], '営業中', ['営業中','営業しています','開店中'], []),
    ('mention','development',20,'#ffffff','#16202a','Community request',
     ['Please work with @Adobe to make', 'all creative apps work on Linux.'],
     '@Adobeと協力して、すべてのクリエイティブアプリをLinuxで動かせるようにしてください。', ['協力'], ['@Adobe','Linux']),
    ('retry','development',12,'#20232b','#b6bbc7','Connection status',
     ['Retry in 30 seconds'], '30秒後に再試行', ['再試行','リトライ'], ['30']),
    ('file','evaluation',22,'#f1f4f8','#172232','ファイルを選択',
     ['Open'], '開く', ['開く'], []),
    ('discount','evaluation',20,'#17202b','#f0f2f5','Annual plan: pay 20% less',
     ['Save'], '節約', ['節約','割引','お得'], []),
    ('permission','evaluation',16,'#ffffff','#16202a','Terminal output',
     ['Permission denied.', 'Ask the administrator for access.'],
     'アクセスが拒否されました。管理者にアクセス権を依頼してください。', ['管理者'], []),
    ('quest','evaluation',24,'#261c18','#f8ecd9','Village elder',
     ['Bring 3 herbs before sunset.', 'Do not enter the northern cave.'],
     '日没までに薬草を3つ持ってきてください。北の洞窟には入らないでください。', ['入らない'], ['3']),
]


def build(out):
    out.mkdir(mode=0o700,parents=True,exist_ok=True)
    cases=[]
    for name,split,size,bg,fg,heading,body,translated,accepted,protected in CASES:
        image=Image.new('RGB',(1000,420),bg)
        draw=ImageDraw.Draw(image)
        font=ImageFont.truetype(FONT,size)
        lines=[]
        for i,text in enumerate([heading]+body):
            # Space separates heading and body; body lines are adjacent.
            x,y=48,40 if i==0 else 125+(i-1)*(size+5)
            draw.text((x,y),text,font=font,fill=fg,anchor='lt')
            l,t,r,b=draw.textbbox((x,y),text,font=font,anchor='lt')
            lines.append(dict(id=f'{name}-{i}',text=text,x=l,y=t,width=r-l,height=b-t,confidence=1.0))
        selected=lines[1:]
        left=min(r['x'] for r in selected);top=min(r['y'] for r in selected)
        group=dict(id=selected[0]['id'],text=' '.join(body),x=left,y=top,
                   width=max(r['x']+r['width'] for r in selected)-left,
                   height=max(r['y']+r['height'] for r in selected)-top,
                   members=[r['id'] for r in selected],confidence=1.0,
                   accepted=accepted,protected=protected)
        path=out/f'{name}.png';image.save(path)
        cases.append(dict(id=name,split=split,image=str(path.resolve()),lines=lines,
                          groups=[group],translations={group['id']:translated}))
    (out/'truth.json').write_text(json.dumps(dict(version=1,annotation='agent-authored synthetic; not human-reviewed',cases=cases),ensure_ascii=False,indent=2))
    return cases

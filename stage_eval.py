"""Independent stage metrics. Rubric matches are NOT human semantic judgments."""
import re


def score_groups(truth, found):
    expected=[set(group) for group in truth]
    actual=[set(group['members']) for group in found]
    used=set()
    exact=0
    for group in truth:
        match=next((i for i,candidate in enumerate(found) if i not in used and candidate['members']==group),None)
        if match is not None:
            exact+=1
            used.add(match)
    return dict(total=len(expected),exact=exact,
                missing=sum(not any(group & candidate for candidate in actual) for group in expected),
                split=sum(sum(bool(group & candidate) for candidate in actual)>1 for group in expected),
                merged=sum(sum(bool(group & candidate) for group in expected)>1 for candidate in actual),
                extra=sum(not any(group & candidate for group in expected) or candidate in actual[:i]
                          for i,candidate in enumerate(actual)))


def score_translations(truth, translations, rendered):
    shown={row['id'] for row in rendered if row['shown']}
    result=dict(total=len(truth),missing=0,rubric_match=0,protected_failures=0,shown=0,useful_shown=0)
    for row in truth:
        value=translations.get(row['id'],'')
        present=bool(value.strip())
        matched=(present and any(word in value for word in row['accepted'])
                 and not any(word in value for word in row.get('forbidden',[])))
        protected=all(re.search(r'(?<![A-Za-z0-9_.])'+re.escape(token)+r'(?![A-Za-z0-9_]|\.[0-9])',value)
                      for token in row.get('protected',[]))
        visible=row['id'] in shown
        result['missing']+=not present
        result['rubric_match']+=bool(matched)
        result['protected_failures']+=present and not protected
        result['shown']+=visible
        result['useful_shown']+=bool(matched and protected and visible)
    return result


def evaluate_case(case, found):
    from PIL import Image
    from benchmark import score
    from paragraphs import paragraphs
    from snapshot import render
    members={i for group in case['groups'] for i in group['members']}
    groups=[g for g in paragraphs(case['lines']) if set(g['members']) & members]
    with Image.open(case['image']) as original:
        image,rendered=render(original,case['groups'],case['translations'])
    return dict(id=case['id'],split=case['split'],ocr=score(case['lines'],found),
                structure=score_groups([g['members'] for g in case['groups']],groups),
                render=score_translations(case['groups'],case['translations'],rendered),
                rendered=rendered,ocr_rows=found),image


def main():
    import argparse
    import json
    from pathlib import Path
    import time
    from ocr_backends import make_rapid,recognize_rapid
    from stage_fixtures import build
    parser=argparse.ArgumentParser(description='Independent local OCR, oracle structure and oracle rendering evaluation')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    cases=build(args.output/'fixtures')
    started=time.monotonic();engine=make_rapid()
    report=dict(annotation='agent-authored synthetic; not human-reviewed',ocr_init_seconds=time.monotonic()-started,cases=[])
    for case in cases:
        started=time.monotonic();found=recognize_rapid(case['image'],engine)
        seconds=time.monotonic()-started
        result,image=evaluate_case(case,found)
        result['ocr_seconds']=seconds
        report['cases'].append(result)
        image.save(args.output/(case['id']+'-oracle-render.png'))
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(case['id'],result['ocr'],result['structure'],result['render'],flush=True)


if __name__=='__main__':
    main()

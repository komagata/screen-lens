"""Opt-in geometric discovery followed by independent local reading."""
from PIL import Image
from partition_tiles import plan_partition_tiles
from corroborated_partitions import partition_rows
from discovery_merge import valid_box


def refine_partitions(image,rows,request,read_line,max_calls=1):
    """request(crop) returns (regions, usage); read_line returns (text, confidence).

    Neither callback may retry cloud requests internally. Only the seed parent
    is eligible for partitioning; unrelated text in the context is ignored.
    """
    if type(max_calls) is not int or not 0<=max_calls<=4:
        raise ValueError('Partition budget must be an integer from 0 to 4')
    if len({r['id'] for r in rows})!=len(rows):
        raise ValueError('Duplicate OCR IDs')
    tiles=plan_partition_tiles(image,rows)
    audit=dict(calls=0,tiles=tiles[:max_calls],skipped_tiles=tiles[max_calls:],
               regions=[],usage=[],plans=[])
    proposals=[];vision_texts={}
    for index,tile in enumerate(audit['tiles']):
        l,t,r,b=tile['box'];scale=tile['scale']
        crop=image.crop(tile['box']).convert('RGB').resize(((r-l)*scale,(b-t)*scale),Image.Resampling.LANCZOS)
        audit['calls']+=1
        regions,usage=request(crop)
        if not isinstance(regions,list) or len(regions)>100 or any(not isinstance(p,dict) for p in regions):
            raise ValueError('Invalid partition regions')
        audit['usage'].append(usage)
        for number,region in enumerate(regions):
            entry=dict(tile=index,candidate=number)
            audit['regions'].append(entry)
            if not valid_box(region,crop.size):
                entry['reason']='invalid-box';continue
            if (region['x']<=1 or region['y']<=1 or region['x']+region['width']>=crop.width-1
                    or region['y']+region['height']>=crop.height-1):
                entry['reason']='tile-edge';continue
            text=region.get('text')
            if not isinstance(text,str) or not text.strip() or len(text)>10000:
                entry['reason']='invalid-text';continue
            part=dict(x=l+region['x']/scale,y=t+region['y']/scale,
                      width=region['width']/scale,height=region['height']/scale)
            parents=[rows[i]['id'] for i in tile['seeds'] if
                rows[i]['x']<=part['x'] and rows[i]['y']<=part['y']
                and part['x']+part['width']<=rows[i]['x']+rows[i]['width']
                and part['y']+part['height']<=rows[i]['y']+rows[i]['height']]
            if not parents:
                entry['reason']='outside-parent';continue
            value,confidence=read_line(image,part)
            identity=f'{index}/{number}'
            part.update(id=identity,parents=parents,text=value,recognition_confidence=confidence)
            proposals.append(part);vision_texts[identity]=text
            entry.update(reason='reread',proposal=part,vision_text=text)
    result,plans=partition_rows(rows,proposals,vision_texts,image.size)
    audit['plans']=plans
    return result,audit

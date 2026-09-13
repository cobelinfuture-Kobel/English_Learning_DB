from __future__ import annotations
import base64, hashlib, json, lzma, math, re
from pathlib import Path

TASK_ID='KET_Data_S1_ChunkCachedFull1398PageSegmentation_ExactKET_S1Acceptance'
STATUS='PASS_KET_DATA_S1_EXACT_PAGE_MEDIA_SEGMENTATION'
XZ_SHA='b557257b09693a65069e42885c4cbe76347a27e5f54c8090b9b94646252d6a04'
JSON_SHA='b915a0af67a57ae8b6b2b3ac7f16d8f2a6466b18bd6a3b41f50d6aa02a232480'
RT=['TEXT','INSTRUCTION','QUESTION','ANSWER_OPTION','TABLE','IMAGE','DIAGRAM']
MT=['IMAGE','AUDIO_REFERENCE','SPEAKING_CARD']
SC=['source_id','drive_file_id','file_name','media_type_code','page_count','segmentation_status']
PC=['page_id','source_index','page_number','width','height','text_mode_code','regions_by_rt','image_seq_start','item_seq_start','item_labels','media_bits']
EXPECTED_REGIONS={'TEXT':1154,'INSTRUCTION':76,'QUESTION':629,'ANSWER_OPTION':181,'TABLE':67,'IMAGE':1572,'DIAGRAM':15}

class S1Error(ValueError): pass

def _root(root=None): return Path(root or Path(__file__).resolve().parents[2])
def _load(root=None):
    base=_root(root)/'data'/'ket'
    b64=''.join((base/f'ket_page_media_segmentation.json.xz.b64.part{i}').read_text('ascii').strip() for i in (0,1))
    xz=base64.b64decode(b64,validate=True)
    assert hashlib.sha256(xz).hexdigest()==XZ_SHA, 'XZ_SHA256_DRIFT'
    raw=lzma.decompress(xz,format=lzma.FORMAT_XZ)
    assert hashlib.sha256(raw).hexdigest()==JSON_SHA, 'JSON_SHA256_DRIFT'
    return json.loads(raw), xz, raw

def _bbox(b):
    return isinstance(b,list) and len(b)==4 and all(isinstance(x,(int,float)) and math.isfinite(x) and abs(x)<1_000_000 for x in b) and b[0]<=b[2] and b[1]<=b[3]

def validate(root=None):
    p,xz,raw=_load(root); e=[]
    if p.get('s')!='ket.data.page_media_segmentation.s1.v1': e.append('SCHEMA')
    if p.get('e')!='compact_arrays_v4': e.append('ENCODING')
    if p.get('t')!=TASK_ID or p.get('c')!='KET_S1.txt': e.append('AUTHORITY')
    if p.get('rt')!=RT or p.get('mt')!=MT: e.append('REGION_MEDIA_CONTRACT')
    if p.get('sc')!=SC or p.get('pc')!=PC: e.append('COLUMN_CONTRACT')
    ic=p.get('ic') or {}
    if ic.get('page_id')!='{source_id}_P{page_number:03d}': e.append('PAGE_ID_CONTRACT')
    if ic.get('image_id')!='KET_IMG_{global_image_seq:06d}': e.append('IMAGE_ID_CONTRACT')
    if ic.get('item_id')!='KET_ITEM_{global_item_seq:06d}': e.append('ITEM_ID_CONTRACT')
    if ic.get('item_image_binding')!='PAGE_IMAGES': e.append('ITEM_IMAGE_BINDING')

    ss=p.get('ss') or []; ps=p.get('ps') or []
    if len(ss)!=34: e.append(f'SOURCES:{len(ss)}')
    src={}
    for i,row in enumerate(ss,1):
        if not isinstance(row,list) or len(row)!=len(SC): e.append(f'SOURCE_SHAPE:{i}'); continue
        sid,drive,name,mcode,n,status=row
        if sid!=f'KET_SRC_{i:06d}' or not drive or not name: e.append(f'SOURCE_ID_LINEAGE:{i}')
        if sid in src: e.append(f'SOURCE_DUP:{sid}')
        src[sid]=row
        if i<=33 and (mcode!=0 or not isinstance(n,int) or n<1): e.append(f'PDF_SOURCE:{sid}')
        if i==34 and (mcode!=1 or n is not None or status!='NOT_APPLICABLE_PDF_PAGE_SEGMENTATION'): e.append('DOCX_SOURCE')

    if len(ps)!=1398: e.append(f'PAGES:{len(ps)}')
    bysrc={i:[] for i in range(34)}; seen=set(); img_next=item_next=1; pdf_text=ocr=audio=speaking=0
    rc={k:0 for k in RT}; reverse_img=reverse_item=0
    for j,row in enumerate(ps,1):
        if not isinstance(row,list) or len(row)!=len(PC): e.append(f'PAGE_SHAPE:{j}'); continue
        pid,si,pn,w,h,tm,regs,istart,qstart,labels,bits=row
        if not isinstance(si,int) or not 0<=si<33: e.append(f'SOURCE_INDEX:{j}'); continue
        sid=ss[si][0]; expected=f'{sid}_P{pn:03d}' if isinstance(pn,int) else ''
        if pid!=expected or not re.fullmatch(r'KET_SRC_\d{6}_P\d{3}',pid or ''): e.append(f'PAGE_ID:{j}')
        if pid in seen: e.append(f'PAGE_DUP:{pid}')
        seen.add(pid); bysrc[si].append(pn)
        if not (isinstance(w,int) and isinstance(h,int) and w>0 and h>0): e.append(f'PAGE_SIZE:{pid}')
        if tm==0: pdf_text+=1
        elif tm==1: ocr+=1
        else: e.append(f'TEXT_MODE:{pid}')
        if not isinstance(regs,list) or len(regs)!=len(RT): e.append(f'REGIONS:{pid}'); continue
        for k,boxes in enumerate(regs):
            if not isinstance(boxes,list): e.append(f'REGION_SHAPE:{pid}:{RT[k]}'); continue
            rc[RT[k]]+=len(boxes)
            if any(not _bbox(b) for b in boxes): e.append(f'BBOX:{pid}:{RT[k]}')
        images=len(regs[5]); questions=len(regs[2])
        if images:
            if istart!=img_next: e.append(f'IMAGE_SEQ:{pid}')
            reverse_img+=images; img_next+=images
        elif istart is not None: e.append(f'IMAGE_ZERO_START:{pid}')
        if not isinstance(labels,list) or len(labels)!=questions or any(not isinstance(x,int) for x in labels): e.append(f'ITEM_LABELS:{pid}')
        if questions:
            if qstart!=item_next: e.append(f'ITEM_SEQ:{pid}')
            reverse_item+=questions; item_next+=questions
        elif qstart is not None: e.append(f'ITEM_ZERO_START:{pid}')
        if not isinstance(bits,int) or bits<0 or bits>3: e.append(f'MEDIA_BITS:{pid}')
        else:
            audio+=bool(bits&1); speaking+=bool(bits&2)
    for i in range(33):
        n=ss[i][4]
        if bysrc[i]!=list(range(1,n+1)): e.append(f'PAGE_SEQUENCE:{ss[i][0]}')

    actual={'source_count':34,'pdf_source_count':33,'non_pdf_source_count':1,'page_count':len(ps),'image_count':img_next-1,'item_count':item_next-1,'pdf_text_pages':pdf_text,'ocr_pages':ocr,'audio_reference_pages':audio,'speaking_card_pages':speaking,'region_counts':rc}
    if p.get('sum')!=actual: e.append('SUMMARY')
    if rc!=EXPECTED_REGIONS: e.append('REGION_TOTALS')
    if img_next-1!=1572 or item_next-1!=629 or reverse_img!=1572 or reverse_item!=629: e.append('IDENTITY_TOTALS')
    if pdf_text!=131 or ocr!=1267: e.append('TEXT_MODE_TOTALS')
    if p.get('cb')!={'raw_page_text_in_github':False,'raw_ocr_text_in_github':False,'raw_images_in_github':False,'source_assets_remain_external':True}: e.append('COPYRIGHT_BOUNDARY')
    if e: raise S1Error('\n'.join(e[:100]))
    return {'task_id':TASK_ID,'status':STATUS,'contract_source':'KET_S1.txt','source_count':34,'pdf_source_count':33,'page_count':1398,'image_count':1572,'item_count':629,'last_image_id':'KET_IMG_001572','last_item_id':'KET_ITEM_000629','pdf_text_pages':131,'ocr_pages':1267,'region_counts':rc,'xz_sha256':hashlib.sha256(xz).hexdigest(),'json_sha256':hashlib.sha256(raw).hexdigest(),'reverse_lookup_contract':'PASS','copyright_boundary':'PASS'}

def test_ket_data_s1_exact_contract():
    r=validate()
    assert r['status']==STATUS and r['contract_source']=='KET_S1.txt'
    assert (r['page_count'],r['image_count'],r['item_count'])==(1398,1572,629)
    assert r['last_image_id']=='KET_IMG_001572' and r['last_item_id']=='KET_ITEM_000629'
    assert r['reverse_lookup_contract']=='PASS' and r['copyright_boundary']=='PASS'

if __name__=='__main__': print(json.dumps(validate(),ensure_ascii=False,indent=2))
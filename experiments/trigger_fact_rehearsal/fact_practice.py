"""Selected call window and facts from unchanged public scientific teachers.

Full teacher answers remain the primary sample. No field is filled, selected or
rewritten for inference, and no development answer enters the training data.
"""
import json

def spans(target):
    wire=json.loads(target)
    canonical=lambda v:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    if canonical(wire)!=target:
        raise ValueError('CANONICAL_FULL_PUBLIC_TEACHER_TARGET_REQUIRED')
    result=[]
    for error in wire['local_analysis']['error_instances']:
        # Locate the complete registered error, so identical windows belonging
        # to different error instances do not become an ambiguous global match.
        error_text=canonical(error);base=target.find(error_text)
        if base<0 or target.find(error_text,base+1)>=0:
            raise ValueError('UNIQUE_PUBLIC_TEACHER_ERROR_SPAN_REQUIRED')
        for key in ('call_window','facts_at_trigger'):
            prefix=canonical(key)+':';part=prefix+canonical(error[key])
            start=error_text.find(part)
            if start<0 or error_text.find(part,start+1)>=0:
                raise ValueError('UNIQUE_PUBLIC_TEACHER_FACT_SPAN_REQUIRED')
            result.append((base+start+len(prefix),base+start+len(part)))
    if not result:
        raise ValueError('NO_PUBLIC_SELECTED_FACTS')
    return sorted(result)

def practice_labels(row,target,tokenizer):
    if row.get('stage') not in ('L-A0','L-A1') or row['view']!='RESEARCH':
        raise ValueError('LOCAL_FULL_TEACHER_ROW_REQUIRED')
    if not tokenizer.is_fast:
        raise ValueError('REGISTERED_FAST_TOKEN_OFFSET_BINDING_REQUIRED')
    encoded=tokenizer(target,add_special_tokens=False,return_offsets_mapping=True)
    ids=encoded['input_ids'];offsets=encoded['offset_mapping']
    if len(ids)!=len(offsets):
        raise ValueError('TOKEN_OFFSET_CARDINALITY')
    prefix=next(i for i,v in enumerate(row['labels']) if v!=-100)
    if row['input_ids'][prefix:prefix+len(ids)]!=ids or row['labels'][prefix:prefix+len(ids)]!=ids:
        raise ValueError('ACTUAL_FULL_TEACHER_TARGET_TOKEN_IDENTITY')
    selected=spans(target);labels=[-100]*len(row['labels'])
    for i,(a,b) in enumerate(offsets):
        if a<0 or b<a or b>len(target):
            raise ValueError('INVALID_CHARACTER_TOKEN_OFFSETS')
        if a<b and any(a<end and b>begin for begin,end in selected):
            labels[prefix+i]=row['labels'][prefix+i]
    count=sum(v!=-100 for v in labels[1:])
    if not 0<count<row['target_tokens']:
        raise ValueError('PARTIAL_PUBLIC_FACT_PRACTICE_BOUNDARY')
    return labels,{'fact_spans':selected,'target_tokens':count,
                   'full_teacher_target_tokens':row['target_tokens'],
                   'full_teacher_answer_unchanged':True,'fact_labels_copied_from_actual_teacher':True,
                   'new_scientific_judgment_or_fact_generated':False}

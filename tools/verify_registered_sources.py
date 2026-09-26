#!/usr/bin/env python3
"""Verify exact registered release files, without following receipt paths."""
from pathlib import Path,PurePosixPath
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    index=json.loads((ROOT/'runtime/REGISTERED_SOURCE_INDEX.json').read_bytes());count=0
    export=json.loads((ROOT/'runtime/PUBLIC_EXPORT.json').read_bytes())
    exclusions={r['path']:r for r in export['excluded']}
    omitted=[]
    for package in index['packages']:
        root=ROOT/package['snapshot'];manifest=root/'PACKAGE_FILES.sha256'
        if sha(manifest)!=package['manifest_sha256']:raise ValueError('PACKAGE_MANIFEST_HASH_MISMATCH:'+package['snapshot'])
        listed={}
        for line in manifest.read_text().splitlines():
            digest,name=line.split(maxsplit=1);p=PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts:raise ValueError('UNSAFE_MANIFEST_PATH')
            if name in listed:raise ValueError('DUPLICATE_MANIFEST_MEMBER')
            listed[name]=digest
        if listed!={m['path']:m['sha256'] for m in package['members']}:raise ValueError('SOURCE_INDEX_MANIFEST_DISAGREEMENT')
        for name,digest in listed.items():
            relative=(root/name).relative_to(ROOT).as_posix()
            if relative in exclusions:
                if exclusions[relative]['sha256']!=digest:raise ValueError('EXCLUDED_SOURCE_HASH_MISMATCH')
                if (root/name).exists():raise ValueError('PRIVATE_EXCLUDED_FILE_PRESENT')
                omitted.append(relative)
                continue
            if sha(root/name)!=digest:raise ValueError('SOURCE_HASH_MISMATCH:'+str(root/name))
            count+=1
    for value in index['additional_sources'].values():
        if sha(ROOT/value['snapshot'])!=value['sha256']:raise ValueError('ADDITIONAL_SOURCE_HASH_MISMATCH')
        count+=1
    result={'status':'PUBLIC_REGISTERED_SOURCE_HASHES_VERIFIED','packages':len(index['packages']),'source_members':count,
            'explicitly_omitted_private_members':len(omitted),'full_historical_bundle_present':not omitted,
            'source_repository_base':index['repository_base'],'production_execution_started':False}
    print(json.dumps(result,indent=2));return result
if __name__=='__main__':main()

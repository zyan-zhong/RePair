#!/usr/bin/env python3
"""Check the revised manuscript's build, anonymous metadata and numerical data."""
from pathlib import Path
import hashlib,json,re
from pypdf import PdfReader
from reproduce_results import main as reproduce
R=Path(__file__).resolve().parent
def active_files():
    seen=set()
    def walk(p):
        if p in seen:return
        seen.add(p)
        text=re.sub(r'(?<!\\)%[^\n]*','',p.read_text(encoding='utf8'))
        for n in re.findall(r'\\input\{([^}]+)\}',text):
            c=R/n;walk(c if c.suffix else c.with_suffix('.tex'))
    walk(R/'main.tex');return seen
def main():
    numerical=reproduce();log=(R/'main.log').read_text(errors='replace');aux=(R/'main.aux').read_text()
    pdf=PdfReader(R/'main.pdf');texts=[p.extract_text() for p in pdf.pages];text='\n'.join(texts)
    mainpages=int(re.search(r'\\newlabel\{maintextend\}\{\{[^}]*\}\{(\d+)\}',aux)[1])
    src='\n'.join(p.read_text() for p in active_files())
    compact=re.sub(r'\s+','',text)
    resultkeys=set(re.findall(r'\\setresult\{([^}]+)\}',(R/'results/results.tex').read_text()))
    # The definition's formal parameter is not a result use.
    used=set(re.findall(r'\\res\{([^}]+)\}',src))-{'#1'}
    styles=json.loads((R/'STYLE_HASHES.json').read_bytes())
    bibliography=(R/'references.bib').read_text(encoding='utf8')
    bib_urls=set(re.findall(r'url\s*=\s*\{([^}]+)\}',bibliography))
    pdf_urls={str(a.get_object()['/A']['/URI']) for p in pdf.pages for a in p.get('/Annots',[]) if a.get_object().get('/A',{}).get('/URI')}
    checks={
        'main_text_at_most_9_pages':mainpages<=9,
        'no_overfull_boxes':not re.search(r'Overfull \\[hv]box',log),
        'no_undefined_references_or_citations':not re.search(r'(?:Reference|Citation) .+ undefined|There were undefined references|undefined citations',log),
        'no_duplicate_labels':'multiply defined' not in log,
        'no_visible_placeholders':not re.search(r'PENDING|\bTODO\b|\bTBD\b',text),
        'result_keys_defined':used<=resultkeys,
        'anonymous_author':pdf.metadata.author=='Anonymous authors',
        'figure_metadata_anonymous':all(not PdfReader(p).metadata or not any(PdfReader(p).metadata.get(k) for k in ['/Author','/Title','/Subject','/Keywords']) for p in (R/'figures').glob('*.pdf')),
        'no_known_private_identity':not re.search(r'/data/(?:home|run)|[A-Z]:\\Users\\',text,re.I),
        'official_style_unchanged':all(hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in styles.items()),
        'all_24_reference_urls_clickable_in_pdf':len(bib_urls)==24 and bib_urls<=pdf_urls,
        'AI_statement_present':'AIUSESTATEMENT' in compact,
        'negative_selection_reported':'3 / 355' in text,
        'numerical_reproduction':numerical['checks_passed'],
        'appendix_after_references':0<=compact.find('REFERENCES')<compact.find('REPAIRTESTSANDTRAININGDETAILS'),
    }
    report={'main_text_pages':mainpages,'total_pages':len(pdf.pages),'checks':checks,'failed':[k for k,v in checks.items() if not v],
            'scientific_limitations':['Final RePair benchmark absent','Matched component ablations absent','One candidate and one selection seed','Campaign required human recovery and contains one promotion exception'],
            'formal_submission_uploaded':False}
    (R/'verification_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0 if all(checks.values()) else 1
if __name__=='__main__':raise SystemExit(main())

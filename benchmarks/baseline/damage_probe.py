import json,tempfile
from dataclasses import asdict
from pathlib import Path
import numpy as np
from scipy import ndimage
from pkg_re.bga_sample import create_bga_sample
from pkg_re.bga_render import render_layer
from pkg_re.models import Analyze,AutoReview
from pkg_re.operations import analyze_layer
from pkg_re.net_review import refresh_recommendations
from pkg_re.batch_review import auto_review
from pkg_re.store import Store
from pkg_re.engine.masks import connected_regions
with tempfile.TemporaryDirectory() as d:
 s=Store(Path(d)); state=s.create('probe'); fixture=create_bga_sample(state,s,'damaged')
 for l in state.project.layers: analyze_layer(state,s,l.id,Analyze())
 result=[]
 for i,l in enumerate(state.project.layers):
  refresh_recommendations(state,l.id); px=state.pixels[l.id]; rendered=render_layer(fixture.layers[i],'damaged',i)
  hl,hr=connected_regions(ndimage.binary_fill_holes(px.observed)&~px.observed)
  events=[]
  for e in rendered.events:
   x,y,w,h=e.bbox
   hits=[{'bbox':c.bbox,'kind':c.kind,'recommendation':c.recommendation,'reason':c.recommendation_reason} for c in l.candidates if c.bbox[0]<x+w and c.bbox[0]+c.bbox[2]>x and c.bbox[1]<y+h and c.bbox[1]+c.bbox[3]>y]
   ids=set(np.unique(hl[y:y+h,x:x+w]))-{0}
   events.append(dict(asdict(e),candidates=hits,enclosed_holes=[{'bbox':r.bbox,'pixels':r.pixels} for r in hr if r.id in ids]))
  auto_review(state,l.id,AutoReview(expected_revision=state.project.revision))
  result.append({'layer':i,'events':events,'summary':l.review_summary.model_dump(),'added_px':int(px.added.sum()),'recovered_px':int((px.added&rendered.removed).sum()),'false_added_px':int((px.added&~np.logical_or.reduce([n.mask for n in fixture.layers[i].nets])).sum())})
 print(json.dumps(result,indent=2))

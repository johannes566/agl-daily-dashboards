import json,os
_P=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','data','hamper_bom.json')
BOM={k:[(n,float(q)) for n,q in v] for k,v in json.load(open(_P)).items()}

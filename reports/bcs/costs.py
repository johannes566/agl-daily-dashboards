import json,glob
P={'009/RIC003/0250':62.60,'023/ILL001/0025':521.70,'019/TWINSAVER/2':262.88,'009/NES015/0200':171.30,
'023/SEL003/0010':208.65,'009/RIC007/1500':208.65,'019/TOI001/0048':218.00,'019/NAM008/0001':461.50,
'001-1082':135.70,'005/AQUA/1000':130.00,'024/FRE001/0160':94.77,'010/MEGACR/25KG':993.75,
'023/SAL001/2500':55.64,'023/SELATI/2KG':46.95,'009/RIC005/0750':140.30,'010/ELL001/1000':82.60,
'023/HUL002/1000':27.82,'009/FRI002/0750':139.99,'006/HAN003/0750':28.69,'006/TOI002/0500':25.21,
'006/SUN012/0750':33.90,'003/VAL004/0500':54.35,'024/GLE001/1000':48.00,'010/CRE001/0750':69.00,
'011/FIV001/1000':70.00,'014/NES008/0004':234.78,'009/NES004/0200':348.02,'017/DAIRYB/LF1':94.95,
'006/SUN004/3000':82.31,'023/BULKSUGA/25':547.82,'022/HUL002/1000':198.95/1.15*1,'BRUSH/0020':155.65,
'PAINT-ENAMEL01':840.61,'STICK/GLUE01':173.04,'FILLER/ACRYLIC01':16.52}
# invoice item code -> bill code
IMAP={'PAINT-ENAMEL':'PAINT-ENAMEL01','STICK/GLUE':'STICK/GLUE01','FILLER/ACRYLIC':'FILLER/ACRYLIC01','BRUSH/002':'BRUSH/0020'}
f=glob.glob('/root/.claude/projects/-home-claude/0fe8e55c-18e9-5e05-bba4-83155c553a8d/tool-results/*ryseof.txt')[0]
t=open(f).read();qs=json.loads(t[t.find('{'):]) if t.strip()[0]=='{' else json.loads(t)
qs=qs.get('quotes',qs) if isinstance(qs,dict) else qs
def split(lines):
    G=[];H=[]
    for c,n,q,a in lines:
        hamp=('hamper' in n.lower() or 'mpact atlantis' in n.lower() or (c.startswith('025/')))
        (H if hamp else G).append((c,n,q,a))
    return G,H
ql=[(l.get('itemCode') or '',l.get('description') or '',float(l.get('quantity') or 0),float(l.get('lineAmount') or 0)) for q in qs for l in q['lineItems']]
# invoiced general lines (ex VAT) from Xero invoices 1-19 Nov (non-hamper)
il=[('ITALIAN/002','Italian Blend 1kg',3,1328.31),('001/DEL/001','Delivery',1,100),
('PAINT/DUL','Dulux',2,2561.14),('FILLER/001','',2,126.4),('GLUE/002','',5,491.7),('BRUSH/002','Hamilton brush',3,625.71),
('POLYCELL/002','',1,251.11),('FISCHER/001','',2,207.4),('SHIELD/003','',1,268),('ROLLER/225','',5,436.9),('DRILL/003','',1,645.35),
('TAPE/003','',10,600.5),('TAPE/004','',5,62.5),('LATEX/003','',1,52.36),('SKREWDRIVER/005','',1,152.29),('SILICONE/003','',10,410),
('DRILL/SET','',1,494.55),('DROMEX/002','',1,14.36),('ALLEN/KEY','',1,190.95),('SOCKET/002','',1,844.3),('MASK02','',5,173.7),
('LADDER/003','',1,2076.79),('PRETLEY/003','',1,99.03),('STICK/GLUE','Evo-Stik',1,322.75),('PAINT-ENAMEL','Dark grey enamel',1,856.43),
('PRIMER/001','',1,523.17),('FILLER/ACRYLIC','Sealant',2,66.04),('CABLE/002','',4,187.36),('TILES/002','',4,6644.24),('001/DEL/001','Delivery',1,100),
('FOAM/CUPS','',3,281.88),('HOTDOG','',1,208.68),('005/DIS001/2500','',1,63.39),('005/DIS002/0250','',1,63.7),('FOMO29','',5,427.1),
('019/NAM008/0001','Np391',11,5332.47),('019/TOI001/0048','1ply',13,3744),
('ORANGES','',1,86.62),('APPLE/02','',1,51.62),('BANA001','',1,97.26),('LEMON010','',1,60.78),('PEACHES/002','',1,110.94),('001/DEL/001','Delivery',1,100),
('0001/CUPCAKES090','Cupcakes',50,1400),('001-1082','refuse',20,4580),('005/AQUA/1000','water',2,520),('001/DEL/001','Delivery',1,100)]
def cost(lines):
    tot=sa=real_sa=real_c=0;rows=[]
    for c,n,q,a in lines:
        k=IMAP.get(c,c)
        if k in P: cc=P[k]*q;real_sa+=a;real_c+=cc;src='LPP'
        else: cc=a*.65;src='35%'
        tot+=cc;sa+=a;rows.append((c,n,q,a,cc,src))
    return sa,tot,real_sa,real_c,rows
if __name__=='__main__':
    qg,qh=split(ql)
    for nm,L in (('quote general',qg),('quote hamper',qh)):print(nm,round(sum(x[3] for x in L),2))
    r=cost(qg);print('quoted gen: sales',round(r[0],2),'cost',round(r[1],2),'real sales',round(r[2],2),'real cost',round(r[3],2))
    for x in sorted(r[4],key=lambda x:-x[3])[:30]:print(x[0],round(x[3]),round(x[4]),x[5],round(1-x[4]/x[3],2))
    ri=cost(il);print('inv gen sales',round(ri[0],2),'cost',round(ri[1],2),'real',round(ri[2],2),round(ri[3],2))

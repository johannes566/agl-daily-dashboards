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
def split(lines):
    G=[];H=[]
    for c,n,q,a in lines:
        hamp=('hamper' in n.lower() or 'mpact atlantis' in n.lower() or (c.startswith('025/')))
        (H if hamp else G).append((c,n,q,a))
    return G,H
def cost(lines):
    tot=sa=real_sa=real_c=0;rows=[]
    for c,n,q,a in lines:
        k=IMAP.get(c,c)
        if k in P: cc=P[k]*q;real_sa+=a;real_c+=cc;src='LPP'
        else: cc=a*.65;src='35%'
        tot+=cc;sa+=a;rows.append((c,n,q,a,cc,src))
    return sa,tot,real_sa,real_c,rows

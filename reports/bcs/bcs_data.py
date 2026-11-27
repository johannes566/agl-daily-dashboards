import json,glob,sys
sys.path.insert(0,'/home/claude/dash2')
T='/root/.claude/projects/-home-claude/0fe8e55c-18e9-5e05-bba4-83155c553a8d/tool-results/'
# ---- invoices 1-27 Nov (page 1 from file, page 2 from the second call) ----
p1=json.load(open(T+'mcp-Xero-get_invoices-1795773608741-0d0hln.txt'))['invoices']
INV=[]
for i in p1:
    if i['status'] in('VOIDED','DELETED','DRAFT'):continue
    INV.append((i['invoice_number'],i['invoice_date'],[(l.get('item_code') or '',l.get('description') or '',float(l['quantity']),float(l['line_amount_net'])) for l in i['line_items']]))
P2=[('INV-0491','2026-11-25',[('006/HAN003/0750','Handy andy liquid scourer 1x750ml',5,124.75),('006/TOI002/0500','Toilet duck assorted 1x500ml',10,314.6),('006/RAD001/0300','Radox Liquid Handsoap 300ml',10,489.0),('006/SUN012/0750','Sunlight dishwasher liquid 1x750ml',5,190.15),('MRMIN','Mr Min Multi Surface Cleaner',10,684.2)]),
('INV-0492','2026-11-26',[('017/DAIRYB/FC1','FAIR CAPE Full Cream Milk 6 x 1Lt',2,266.0),('023/HUL003/2500','Huletts white sugar 2.5kg',2,160.7),('014/BOK002/0500','Rusks 1x450g',2,139.72),('024/FRE001/0080','Freshpak teabags 80x2.5g',1,69.04),('013/FILTERP003','Perco Coffee Filter Paper',2,151.38),('009/JOC001/0200','Jacobs Kronung inst Coffee 200g',2,463.64),('030/BAXTONS/100','Baxtons Pom Pom Candy',1,66.36),('001/DEL/001','DELIVERY FEE',1,100.0)]),
('INV-0495','2026-11-27',[('025/GLASSP/EPP','Glass Partners Epping Mix Hamper',34,2801.94),('001/DEL/001','DELIVERY FEE',1,100.0)]),
('INV-0496','2026-11-27',[('025/ACT/001','Act Logistics Coffee Hampers',160,14332.8)]),
('INV-0497','2026-11-27',[('025/TRIP/001','Triple 5 Coffee Hamper',2,189.28),('025/COM001/0001','Compass Glass Hamper',21,2473.8),('017/DAIRYB/FC1','FAIR CAPE Full Cream Milk 6 x 1Lt',2,270.0)])]
INV+=P2
il_all=[(('LECTURE' if (l[1].strip().startswith('LPFNQF6') or l[1].strip().startswith('ASSESSMENT:')) else l[0]),)+tuple(l[1:]) for _,_,ls in INV for l in ls]  # USB lecture income (account 40654505), no cost of sale
# ---- accepted quotes: API date >= 31 Oct (= 1 Nov on screen) ----
qq=json.load(open(T+'mcp-remote-devices-agl-xero__xero_list_accepted_quotes-1795773634567-6rsu7k.txt'))['quotes']
QS=[q for q in qq if q['status']=='ACCEPTED' and q['date']>='2026-10-31']
def qlines(qs): return [(l.get('itemCode') or '',l.get('description') or '',float(l.get('quantity') or 0),float(l.get('lineAmount') or 0)) for q in qs for l in q['lineItems']]
# ---- exclude accepted-quote lines already invoiced (Xero leaves the quote ACCEPTED when the invoice is keyed separately) ----
_used=set(); MATCHED=[]
_OK={('QU-0364','INV-0480'),('QU-0366','INV-0485')}  # same contact AND same reference name on quote and invoice (verified)
def _is_inv(qn,qdate,l):
    d=(l.get('description') or '').strip().lower(); qty=round(float(l.get('quantity') or 0),2); amt=float(l.get('lineAmount') or 0)
    if not d or 'delivery' in d: return None
    for num,dt,lines in INV:
        if dt<qdate: continue
        for j,(c,n,q,a) in enumerate(lines):
            if (num,j) in _used or (qn,num) not in _OK: continue
            if n.strip().lower()==d and round(q,2)==qty and abs(a-amt)<=0.12*max(amt,1):
                _used.add((num,j)); return num
    return None
_QSX=[]
for q in QS:
    keep=[]
    for l in q['lineItems']:
        n=_is_inv(q['quoteNumber'],q['date'],l)
        if n: MATCHED.append((q['quoteNumber'],n,l.get('description'),float(l.get('lineAmount') or 0)))
        else: keep.append(l)
    _QSX.append(dict(q,lineItems=keep))
QS_ALL=QS; QS=_QSX
ql_all=qlines(QS)
# today = screen date 27 Nov = API date 26 Nov
QT=[q for q in QS if q['date']=='2026-11-26']
tl=qlines(QT)
# ---- bank postings 1-27 Nov ----
b=json.load(open(T+'mcp-remote-devices-agl-xero__xero_list_bank_transactions-1795773601225-p17cgz.txt'))
rows=[]
for t in b['bankTransactions']:
    if t['type']=='SPEND' and t['status'] not in('DELETED','VOIDED') and '2026-11-01'<=t['date']<='2026-11-27':
        inc=t.get('lineAmountTypes')=='Inclusive'
        for l in t['lineItems']: rows.append((t['date'],(t.get('contact') or {}).get('name') or '',str(l.get('accountCode')),l['lineAmount']-((l.get('taxAmount') or 0) if inc else 0),l.get('description') or ''))
if __name__=='__main__':
    print(len(INV),'invoices',len(QS),'quotes',len(QT),'today quotes',len(rows),'spend lines')
    print('inv total',round(sum(l[3] for l in il_all),2),'quotes total',round(sum(l[3] for l in ql_all),2),'today',round(sum(l[3] for l in tl),2))
    for q in QT: print(q['quoteNumber'],q['date'],q['contact']['name'],q['subTotalExcludingTax'])
    from collections import defaultdict
    d=defaultdict(float)
    for r in rows: d[(r[2])]+=r[3]
    print(sorted(((round(v,2),k) for k,v in d.items()),reverse=True))
    print([ (r[0],r[1],round(r[3],2),r[2]) for r in rows if r[2] not in('40654688','40654689','40654727','38778349','38778350','38778344')])

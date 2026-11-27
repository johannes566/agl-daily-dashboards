import datetime as dt, calendar, sys
from collections import defaultdict
sys.path.insert(0,'/home/claude')
import bpos_fc_build as B
from openpyxl import Workbook
from openpyxl.styles import Font,PatternFill,Alignment
nb,md=B.nb,B.md
START,END=B.START,B.END
L0=-1155815.19  # restores the Nov loss in full; the R60,000 of 13 Nov covered October
OPEN=B.OPEN
months=B.months
# COO 20 Nov: November fixed costs already paid; only salaries still due in November
import datetime as _dt
for _d in list(B.pay):
    if _d<=_dt.date(2026,11,30):
        B.pay[_d]=[(l,a) for l,a in B.pay[_d] if l=='Salaries (gross)']
        if not B.pay[_d]: del B.pay[_d]
LOAN_D=_dt.date(2026,12,14);LOAN=119480.50
def run(cust,loan=False,nov_extra=0.0):
    r=defaultdict(float);rv=defaultdict(float)
    for y,m in months[1:]:
        d=nb(md(y,m,5));
        if START<=d<=END:r[d]+=cust
        d=nb(md(y,m,16))
        if START<=d<=END:rv[d]+=50000.0
    rv[_dt.date(2026,11,27)]+=50000.0
    if nov_extra: r[_dt.date(2026,11,27)]+=nov_extra
    ln=defaultdict(float)
    if loan: ln[LOAN_D]+=LOAN
    fb=set()
    for y,m in months:
        d=nb(md(y,m,1))
        if (y,m)!=(2026,11) and START<=d<=END: fb.add(d)
    rows=[];bal=OPEN
    acc=(1204663.94*2+1228435.39)*0.1875/365*0.84
    post={nb(md(y,m,14)) for y,m in months[1:]}
    d=START
    while d<=END:
        o=bal
        acc+=max(0,-o)*0.1875/365*0.84
        intr=0.0;notes=[]
        if d in post: intr=round(acc,2);acc=0.0;notes.append(f'Net overdraft interest {intr:,.2f}')
        fee=sum(a for _,a in B.other.get(d,[]))
        if fee: notes.append('Monthly credit fee 1,625.00')
        p=sum(a for _,a in B.pay.get(d,[]))
        notes+=[f'{l} {a:,.2f}' for l,a in B.pay.get(d,[])]
        rep=round(max(0,L0-o),2) if d in fb else 0.0
        if rep: notes.insert(0,f'Shareholder replenishment {rep:,.2f} (assumed)')
        if r.get(d): notes.append(f'Customer receipts {r[d]:,.2f}')
        if rv.get(d): notes.append('Salary recovery: Butlers Catering 20,000.00; Novexa 30,000.00'+(' (November, date assumed)' if d.month==11 else ''))
        if ln.get(d): notes.append(f'Loan repayment from Butlers Catering {ln[d]:,.2f} (MANAGEMENT-REPORTED, not authorised)')
        oth=round(intr+fee,2)
        bal=round(o+r.get(d,0)+rv.get(d,0)+ln.get(d,0)-p-oth+rep,2)
        conf=[]
        if r.get(d): conf.append('Medium: management-reported customer receipts')
        if rv.get(d): conf.append('Medium: COO-confirmed recoveries, no bank history yet')
        if p: conf.append('High: recurring debit orders, payroll, wages')
        if intr: conf.append('Medium: interest depends on balance')
        if rep: conf.append('Assumption: shareholders replenish the prior month loss')
        rows.append((d,round(o,2),round(r.get(d,0),2),round(rv.get(d,0)+ln.get(d,0),2),round(p,2),oth,rep,bal,'; '.join(conf) if conf else 'High: no scheduled movements','; '.join(notes) if notes else ('Last bank evidence: FNB statement 16 Nov' if d==START else ''),1 if d in fb else 0))
        d+=dt.timedelta(1)
    return rows
data={'Base':run(115680.0,False,42301.50),'Downside':run(20352.0)}

import sys;sys.path.insert(0,'/home/claude/dash2')
import json
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus.flowables import Flowable
import bcs_data as D, costs as K, hcost as H, lpp_nov27
OUT='/home/claude/out/Butlers_Catering_Daily_Finance_Dashboard_2026-11-27.pdf'
rows=D.rows
def s(pred): return round(sum(r[3] for r in rows if pred(r)),2)
low=lambda r,k:k in r[1].lower()
sal=s(lambda r:r[2] in('40654688','40654689','40654727'))
disc=s(lambda r:low(r,'disclife'))
ins=s(lambda r:r[2]=='38778349')-disc
intr=s(lambda r:r[2]=='38778350')
bank=s(lambda r:r[2]=='38778344')
fhbc=s(lambda r:low(r,'netcash'))
afri=s(lambda r:low(r,'afriforum'))
m24=s(lambda r:low(r,'media 24'))
nas=s(lambda r:low(r,'nashua'));sec=s(lambda r:low(r,'secur'));acc=s(lambda r:low(r,'accountab'));nea=s(lambda r:low(r,'neasa'))
FUEL=1000+800+800+800+1000+1000+400   # Absa Fleet card POs 1-27 Nov, ex VAT (VAT-free)
BUD=[('Salaries, wages and PAYE',sal,168896.45),('Marwel Intercompany',29576.96,29576.96),('Rental',23000,23000),('BPOS salary recovery',0,20000),('Trinesoft Technologies',15000,15000),('Fuel',FUEL,21000),('Discovery Life',disc,7183.31),('Nashua',nas,4279.10),('Insurance',ins,3788.84),('Overdraft interest',intr,2822.57),('Bank charges',bank,2211.91),('FHBC BEE',fhbc,1035.00),('BGEFS',561.74,561.74),('Afriforum',afri,521.74),('Media 24',m24,489.18),('Securetrac',sec,470.00),('Accountability',acc,359.13),('NEASA',nea,310.43)]
FXB=sum(b for _,_,b in BUD); FXS=sum(x for _,x,_ in BUD); print('fixed',round(FXS,2),round(FXB,2),[(n,round(x,2)) for n,x,_ in BUD])
# ---- sales ----
ig,ih=K.split(D.il_all); qg,qh=K.split(D.ql_all)
inv_g=sum(x[3] for x in ig);inv_h=sum(x[3] for x in ih);q_g=sum(x[3] for x in qg);q_h=sum(x[3] for x in qh)
ri=K.cost(ig);rq=K.cost(qg);hi=H.hcost(ih);hq=H.hcost(qh)
tg,th=K.split(D.tl);today=sum(x[3] for x in D.tl);rt=K.cost(tg);hh=H.hcost(th) if th else (0,0,0,0,.65,[]);todayc=rt[1]+hh[1]
tgt=1250000; td,tt=20,21; rem=2; C=0.65   # today and Monday still open
bsk=inv_g+inv_h+q_g+q_h
print('invoiced gen/ham',round(inv_g,2),round(inv_h,2),'quoted gen/ham',round(q_g,2),round(q_h,2),'basket',round(bsk,2))
print('cost gen inv',round(ri[1],2),'gen q',round(rq[1],2),'ham inv',round(hi[1],2),'ham q',round(hq[1],2))
print('GP% basket',round((1-(ri[1]+rq[1]+hi[1]+hq[1])/bsk)*100,1),'today',today)
print('general priced share inv',round(ri[2]/ri[0]*100,1),'quote',round(rq[2]/rq[0]*100,1),'hamper priced share inv',round(hi[2]/hi[0]*100,1),'quote',round(hq[2]/hq[0]*100,1))
def R(v,dec=2): return ('-R{:,.2f}' if v<0 else 'R{:,.2f}').format(abs(v))
INK='#1A1A1A';MUT='#666666';LINE='#D9D9D9';TEAL='#1B6B5F';RED='#B3261E'
def P(t,sz=8.6,b=False,c=INK,al=0,f=None):
    fn=f or ('Helvetica-Bold' if b else 'Helvetica')
    return Paragraph(t,ParagraphStyle('x',fontName=fn,fontSize=sz,leading=sz+2.4,textColor=colors.HexColor(c),alignment=al))
def N(t,b=False,c=INK,sz=8.6): return P(t,sz,b,c,2,'Courier-Bold' if b else 'Courier')
class Bar(Flowable):
    def __init__(s,f,w=70*mm,h=2.6*mm): s.f=f;s.w=w;s.h=h
    def wrap(s,a,b): return s.w,s.h
    def draw(s):
        c=s.canv;c.setFillColor(colors.HexColor('#E7E7E7'));c.roundRect(0,0,s.w,s.h,1,stroke=0,fill=1)
        c.setFillColor(colors.HexColor(RED if s.f>1 else TEAL));c.roundRect(0,0,s.w*min(s.f,1),s.h,1,stroke=0,fill=1)
def card(inner,w=182*mm):
    t=Table([[inner]],colWidths=[w]);t.setStyle(TableStyle([('BOX',(0,0),(-1,-1),.6,colors.HexColor(LINE)),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),6)]));return t
def lab(t): return P(t,7.3,True,'#444444')
doc=SimpleDocTemplate(OUT,pagesize=A4,leftMargin=14*mm,rightMargin=14*mm,topMargin=12*mm,bottomMargin=12*mm,title='Butlers Catering Daily Finance Dashboard')
S=[P('Butlers Catering Daily Finance Dashboard',15,True),
P('Butlers Catering, rand excluding VAT, November 2026 month to date (1 to 27 Nov)',8,False,MUT),
P('Day 27 of 30 | trading day 20 of 21',8,False,MUT,0,'Courier'),Spacer(1,3*mm)]
def sr(l,sub,sa,mgn=True,b=False,cost=None):
    cost=sa*C if cost is None else cost;g=sa-cost
    return [[P(l,8.6,b),N(R(sa),b),N(R(cost),b),N(R(g),b),N('%.1f%%'%(g/sa*100),True)],
            [P(sub,7,False,MUT),'','','','']]
data=[['',P('Sales',7.5,True,MUT,2),P('Cost of sale',7.5,True,MUT,2),P('GP Rand',7.5,True,MUT,2),P('GP margin',7.5,True,MUT,2)]]
def add(l,sub,sa,b=False,cost=None):
    a,c=sr(l,sub,sa,b=b,cost=cost); data.append(a)
data.append([P('General goods',9,True),'','','',''])
add('Invoiced','',inv_g,cost=ri[1])
add('Quoted, not yet invoiced','',q_g,cost=rq[1])
add('General goods weighted GP margin','',inv_g+q_g,True,cost=ri[1]+rq[1])
data.append([P('Hampers',9,True),'','','',''])
add('Invoiced','',inv_h,cost=hi[1])
add('Quoted, not yet invoiced','',q_h,cost=hq[1])
add('Hampers weighted GP margin','',inv_h+q_h,True,cost=hi[1]+hq[1])
add('Weighted GP margin, entire basket','',bsk,True,cost=ri[1]+rq[1]+hi[1]+hq[1])
t=Table(data,colWidths=[74*mm,27*mm,27*mm,27*mm,21*mm])
st=[('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),1.5),('BOTTOMPADDING',(0,0),(-1,-1),1.5),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor(INK))]
for i,r in enumerate(data):
    if i>0 and r[1]!='' and i%2==0: pass
t.setStyle(TableStyle(st))
S.append(card([lab('SALES AND GROSS PROFIT'),Spacer(1,2),t]));S.append(Spacer(1,3*mm))
def big(l,v,sub=''):
    return [lab(l),P(v,14,True,INK,0,'Courier-Bold')]+([P(sub,7.3,False,MUT)] if sub else [])
lt=Table([[ [lab('Sales'),P(R(today),13,True,INK,0,'Courier-Bold')],[lab('Cost of sale'),P(R(todayc),13,True,INK,0,'Courier-Bold')],[lab('GP Rand'),P(R(today-todayc),13,True,INK,0,'Courier-Bold')],[lab('GP margin'),P(('%.1f%%'%((today-todayc)/today*100)) if today else '-',13,True,INK,0,'Courier-Bold')]]],colWidths=[45*mm]*4)
S.append(card([lab('SALES LOADED TODAY (27 NOV)'),Spacer(1,2),lt,Spacer(1,0)]));S.append(Spacer(1,3*mm))
gap=max(0,tgt-bsk)
nd=Table([[ [lab('Sales to be won per trading day'),P(R(gap/rem),15,True,INK,0,'Courier-Bold')],[lab('Shortfall to the R1,250,000 target'),P(R(gap),15,True,RED if gap else INK,0,'Courier-Bold')],[lab('Trading days left'),P(str(rem),15,True,INK,0,'Courier-Bold')] ]],colWidths=[70*mm,70*mm,38*mm])
S.append(card([lab('SALES NEEDED UNTIL MONTH END'),Spacer(1,2),nd]));S.append(Spacer(1,3*mm))
W=[44*mm,50*mm,14*mm,34*mm,34*mm]
fd=[['','','',P('Spent',7.5,True,MUT,2),P('Budget',7.5,True,MUT,2)]]
for n,sp,b in BUD:
    f=sp/b
    fd.append([P(n,8.4),[Bar(f,w=46*mm)],N('%.0f%%'%(f*100),True,sz=8.2),N(R(sp),sz=8.2),N(R(b),sz=8.2)])
ft=Table(fd,colWidths=W);ft.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),1.8),('BOTTOMPADDING',(0,0),(-1,-1),1.8),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor(INK))]))
tt_=Table([[P('Total fixed costs',8.8,True),[Bar(FXS/FXB,w=46*mm)],N('%.0f%%'%(FXS/FXB*100),True,sz=8.4),N(R(FXS),True,sz=8.4),N(R(FXB),True,sz=8.4)]],colWidths=W);tt_.setStyle(TableStyle([('LINEABOVE',(0,0),(-1,0),.5,colors.HexColor(INK)),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
note=('From Xero bank postings 1 to 27 Nov. Salaries line holds the Discovery premium of R26,134, Charlene Weavers R2,741.11, casual wages of R1,500 and the weekly wages paid on 6 Nov of R3,771.76. Insurance holds R4,038.42 and a R1,961.82 debit order posted to the insurance account on 9 Nov. '
 'Marwel Intercompany, Rental and Trinesoft Technologies are taken at budget as paid in full, per management. '
 'Not allocated to a line yet: R20,000.00 posted to the Conference Facilities Retainer account on 6 Nov, Xero subscriptions of R3,127.75, Netflix R99.00, airtime R35.00 and Thomas International R2.62. Payroll at month end, fuel and the remaining lines have not yet posted.')
S.append(card([lab('FIXED COSTS AGAINST THE BREAK-EVEN BUDGET'),Spacer(1,2),ft,tt_,]));S.append(Spacer(1,3*mm))
plan=tgt*.35-FXB; app=FXB/tt*td; gpb=bsk-(ri[1]+rq[1]+hi[1]+hq[1])
nt=Table([[ [lab('Planned net profit, November'),P(R(plan),15,True,INK,0,'Courier-Bold')],
 [lab('Actual net profit, month to date'),P(R(gpb-app),15,True,RED if gpb-app<0 else INK,0,'Courier-Bold')] ]],colWidths=[85*mm,92*mm])
S.append(card([lab('NET PROFIT AGAINST PLAN'),Spacer(1,2),nt]));S.append(Spacer(1,3*mm))
S.append(P('Advisory only: no accounting records, payments, approvals, or financial commitments have been changed or executed.',7.5,False,MUT))
doc.build(S)

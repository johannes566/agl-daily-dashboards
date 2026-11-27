import sys,datetime as dt;sys.path.insert(0,'/home/claude')
import bpos_fc2 as X
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus.flowables import Flowable
# ---- bank evidence 1-16 Nov (ex VAT where standard rated) ----
bank=[(7975.49,'Wesbank'),(100,'Toekomsv'),(1299.00,'Multidirect'),(7640.00,'Giba'),(15831.67,'Insurance'),(2065.68,'FNB OBE'),(6050.73,'Marks'),
(1197.11*4,'Wages'),(1343.88,'EPX'),(1189.10,'Sage'),(535.00,'Proforce'),(5000.00,'Retainer'),(18985.30-3037.64,'Interest'),(1625.00,'Credit fee'),(23771.45,'Rent')]
chk=round(sum(a for a,_ in bank),2);print('payments check',chk,'expect 95163.10')
V=1.15
BUD=[('Rent, Maitland warehouse',round(23771.45/V,2),20670.83),('Storage, Kraft Road',0,1710.00),('Storage, Lovemore Bros',0,1500.00),
('Salaries (gross), due 30 Nov',0,51000.00),('Weekly wages',4788.44,7182.66),('Consulting retainer',5000.00,20000.00),
('Vodacom',0,14416.69),('Wesbank 7252',7975.49,7975.49),('Securetrac',0,705.00),('Fuel (JHB)',0,500.00),('Insurance (VERS)',round(15831.67/V,2),13766.67),
('ADT security',0,2102.85),('Sage VIP',round(1189.10/V,2),1034.00),('Multidirect',round(1299/V,2),1129.57),('Proforce',round(535/V,2),465.22),('Toekomsv',100.00,100.00),
('EPX Couriers',round(1343.88/V,2),3000.00),('Overdraft interest, net of rebate',round(18985.30-3037.64,2),15947.66),('Bank charges',round(2065.68/V+1625,2),3656.14)]
UNB=[('Giba storage (supplier no longer used)',round(7640/V,2)),('Marks Autocare vehicle repairs',round(6050.73/V,2))]
FXB=sum(b for _,_,b in BUD);FXS=sum(s for _,s,_ in BUD);UN=sum(v for _,v in UNB)
# ---- income statement (paper) ----
oct_inv={'Medpro Pharmaceutica':64225.62+60835.78+6608.54,'West Coast Distillers':12500.00,'African Roots Wine':3424.00,'Cosnova Cosmetix':15390.00,'Meerhof Wines':3200.00,'Funky Ouma':798.74+1314.15+810.76+1288.86}
EXP=sum(oct_inv.values());NONPAY=sum(oct_inv[k] for k in ('Medpro Pharmaceutica','West Coast Distillers','African Roots Wine'));PAYC=EXP-NONPAY
COS=20686.31;REC=50000.00
FXM=FXB+UN
exp_net=EXP-COS+REC-FXM
mtd_net=0-COS-(FXS+UN)
print('EXP',EXP,'NONPAY',NONPAY,'PAYC',PAYC,'FXB',FXB,'FXS',FXS,'UN',UN,'exp_net',exp_net,'mtd_net',mtd_net)
# ---- cash ----
rec_mtd=22542.90;pay_mtd=95163.10;sal=51000.00;COSX=60000.00-17698.50;cash_dn=rec_mtd+REC-pay_mtd-sal;cash_nov=cash_dn+COSX;loan=60000.00;tofund=-cash_nov
print('cash_nov',cash_nov,'tofund',tofund)
# monthly shortages Dec-Feb (normalised for Vodacom/Securetrac shift into Feb)
from collections import defaultdict
SH={}
for k in ('Base','Downside'):
    p=defaultdict(float)
    for r in X.data[k]: p[r[0].strftime('%Y-%m')]+=r[4]+r[5]
    inc=(115680.0 if k=='Base' else 20352.0)+50000.0
    pj=dict(p);pj['2027-01']+=16579.19+810.75
    SH[k]=[max(0,pj[m]-inc) for m in ('2026-12','2027-01','2027-02')]
print(SH)
low={k:min(X.data[k],key=lambda r:r[7]) for k in X.data}
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
        c.setFillColor(colors.HexColor(RED if s.f>1.005 else TEAL));c.roundRect(0,0,s.w*min(s.f,1),s.h,1,stroke=0,fill=1)
def card(inner,w=182*mm):
    t=Table([[inner]],colWidths=[w]);t.setStyle(TableStyle([('BOX',(0,0),(-1,-1),.6,colors.HexColor(LINE)),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),6)]));return t
def lab(t): return P(t,7.3,True,'#444444')
def rows(items,w1,w2):
    d=[[P(a,8.4,b),N(v,b,c,8.2)] for a,v,b,c in items]
    t=Table(d,colWidths=[w1,w2]);t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),('LINEABOVE',(0,len(d)-1),(-1,len(d)-1),.5,colors.HexColor(INK))]));return t
doc=SimpleDocTemplate('/home/claude/out/BPOS_Daily_Finance_Dashboard_2026-11-27.pdf',pagesize=A4,leftMargin=14*mm,rightMargin=14*mm,topMargin=12*mm,bottomMargin=12*mm,title='BPOS Daily Finance Dashboard')
S=[P('Butlers Point of Sale Logistics Daily Finance Dashboard',15,True),
P('Butlers Point of Sale Logistics, rand excluding VAT unless stated, November 2026 month to date (1 to 27 Nov)',8,False,MUT),
P('Day 27 of 30 | trading day 20 of 21 | bank evidence to 16 Nov',8,False,MUT,0,'Courier'),Spacer(1,3*mm)]
# side by side
L=rows([('Customer invoicing to date (invoiced at month end)',R(0),False,INK),
('Expected November invoicing (October run-rate)',R(EXP),False,INK),
('Cost of sale to date',R(-COS),False,INK),
('Salary recovery, BCS and Novexa (other income)',R(REC),False,INK),
('Fixed costs, budget plus unbudgeted paid',R(-FXM),False,INK),
('Expected November net profit',R(exp_net),True,TEAL if exp_net>=0 else RED)],42*mm,26*mm)
Rr=rows([('Customer cash received, 1 to 16 Nov',R(rec_mtd),False,INK),
('Cosnova balance to reach R60,000 (date assumed)',R(COSX),False,INK),
('Salary recoveries still to receive (date assumed)',R(REC),False,INK),
('Payments made, 1 to 16 Nov',R(-pay_mtd),False,INK),
('Salaries still due, 30 Nov',R(-sal),False,INK),
('Expected November cash result',R(cash_nov),True,RED)],42*mm,26*mm)
two=Table([[ [lab('INCOME STATEMENT, ON PAPER (ACCRUAL)'),Spacer(1,2),L],[lab('CASH, IN THE BANK'),Spacer(1,2),Rr] ]],colWidths=[91*mm,91*mm])
two.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEAFTER',(0,0),(0,0),.6,colors.HexColor(LINE)),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(0,0),8),('LEFTPADDING',(1,0),(1,0),8)]))
S.append(card([lab('PROFIT AGAINST CASH, NOVEMBER, SIDE BY SIDE'),Spacer(1,3),two,Spacer(1,3),
P('The two views differ by %s. Of the %s expected to be invoiced, %s is for Medpro, West Coast Distillers and African Roots, who are being invoiced every month and are not paying. Only %s comes from customers who pay (Cosnova, Meerhof Wines, Funky Ouma).'%(R(exp_net-cash_nov),R(EXP),R(NONPAY),R(PAYC)),7.6,False,MUT)]));S.append(Spacer(1,3*mm))
# cash position
ct=Table([[ [lab('FNB balance, 16 Nov (last evidence)'),P(R(-1228435.39),11,True,RED,0,'Courier-Bold')],
[lab('120-day low, base'),P(R(low['Base'][7]),11,True,RED,0,'Courier-Bold'),P(low['Base'][0].strftime('%d %b %Y'),7.3,False,MUT)],
[lab('120-day low, downside'),P(R(low['Downside'][7]),11,True,RED,0,'Courier-Bold'),P(low['Downside'][0].strftime('%d %b %Y'),7.3,False,MUT)],
[lab('Overdraft limit'),P(R(-1300000),11,True,INK,0,'Courier-Bold'),P('reference only',7.3,False,MUT)] ]],colWidths=[44*mm,43*mm,43*mm,52*mm])
S.append(card([lab('CASH POSITION AND 120-DAY LOW POINT'),Spacer(1,2),ct]));S.append(Spacer(1,3*mm))
# fixed costs
W=[44*mm,50*mm,14*mm,34*mm,34*mm]
fd=[['','','',P('Spent',7.5,True,MUT,2),P('Budget',7.5,True,MUT,2)]]
for n,sp,b in BUD:
    f=sp/b
    fd.append([P(n,8.4),[Bar(f,w=46*mm)],N('%.0f%%'%(f*100),True,sz=8.2),N(R(sp),sz=8.2),N(R(b),sz=8.2)])
for n,v in UNB:
    fd.append([P(n,8.4),[Bar(1.1,w=46*mm)],N('n/a',True,RED,8.2),N(R(v),False,RED,8.2),N(R(0),sz=8.2)])
ft=Table(fd,colWidths=W);ft.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),1.6),('BOTTOMPADDING',(0,0),(-1,-1),1.6),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor(INK))]))
tt_=Table([[P('Total fixed costs',8.8,True),[Bar((FXS+UN)/FXB,w=46*mm)],N('%.0f%%'%((FXS+UN)/FXB*100),True,sz=8.4),N(R(FXS+UN),True,sz=8.4),N(R(FXB),True,sz=8.4)]],colWidths=W);tt_.setStyle(TableStyle([('LINEABOVE',(0,0),(-1,0),.5,colors.HexColor(INK)),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
note=('Spent is taken from the FNB statement 1 to 16 Nov, VAT removed from standard-rated items. Lines at nil have not left the FNB account by 16 Nov: either still due (Vodacom, Securetrac and salaries are due 30 Nov) or paid from another BPOS account, to be confirmed. The FNB debit of R2,065.68 on 5 Nov is assumed to be online banking fees. EPX Couriers is added at R3,000 as instructed on 20 Nov. Giba was paid R7,640 on 2 Nov although the supplier is no longer used, and the Marks Autocare repair is outside the budget: both are exceptions requiring explanation.')
S.append(card([lab('FIXED COSTS AGAINST THE APPROVED BUDGET'),Spacer(1,2),ft,tt_,Spacer(1,2),P(note,7.1,False,MUT)]));S.append(Spacer(1,3*mm))
# closing card
sh=Table([[P('',7),P('Dec 2026',7.5,True,MUT,2),P('Jan 2027',7.5,True,MUT,2),P('Feb 2027',7.5,True,MUT,2)],
[P('If customers pay as reported (base)',8.4)]+[N(R(v),sz=8.4) for v in SH['Base']],
[P('If customers pay at the bank-evidenced level (downside)',8.4)]+[N(R(v),sz=8.4) for v in SH['Downside']]],colWidths=[72*mm,36*mm,36*mm,36*mm])
sh.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor(INK))]))
big=Table([[ [lab('Shareholders to cover by 1 December'),P(R(tofund),16,True,RED,0,'Courier-Bold'),P('November cash loss if Cosnova reaches R60,000 for the month. If Cosnova does not pay the balance it is %s. The R60,000 of 13 Nov covered October.'%R(-cash_dn),7.3,False,MUT)] ]],colWidths=[182*mm])
S.append(card([lab('ANTICIPATED CASH LOSS TO BE COVERED BY SHAREHOLDERS NEXT MONTH'),Spacer(1,3),big,Spacer(1,5),lab('FOLLOWING MONTHS, EACH TO BE COVERED BY THE 1ST OF THE NEXT MONTH'),sh,Spacer(1,3),
P('Each month is taken on its own, with no surplus carried forward and the R119,480.50 Butlers Catering loan repayment left out. The base case rests on customer receipts of R115,680 a month as reported by management. The invoices visible in Xero for paying customers come to about %s ex VAT a month (Cosnova, Meerhof Wines, Funky Ouma) and the bank evidenced about R20,352 a month, so the downside is the safer planning figure until the December receipts arrive.'%R(PAYC),7.4,False,MUT)]));S.append(Spacer(1,3*mm))
S.append(P('Advisory only: no accounting records, payments, approvals, or financial commitments have been changed or executed.',7.5,False,MUT))
doc.build(S)

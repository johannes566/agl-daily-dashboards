import re,collections
from bom import BOM
M={'ALU-ABW Mix Hamper + Soap':'Inducote - ALU + Soap','ALU-ABW MIX HAMPER':'Inducote - ALU ','Glass Partners Mixed Hamper Airport':'GLASS PARTNERS AIRPORT','Glass Partners Mixed Hamper Bellville':'GLASS PARTNERS BELLVILLE ','Glass Partners Epping Mix Hamper':'GLASS PARTNERS EPPING','Compass Glass Hamper':'Compass glass Hamper','Compass Glass Hamper 2':'Compass glass  Hamp2 ','Crossroads Distributions Coffee Hamper':'Crossroads','APL Mixed Coffee Hamper':'APL MIX HAMPER','Act Logistics Coffee Hampers':'Act Logistics','MacSteel Mix Hamper':'MACSTEEL MIX HAMPER','Freudenberg Hamper Mix':'FREUDENBER NEW HAMP','Sharp move trading mix hamper':'SHARPMOVE (Davidson)','Sondor Mixed 2 Week Hamper':'Sondor 2 week Mix','Sondor Mixed Hamper':'SONDER INDUSTRIES','Crossroads Epping Mixed Rooibos Hamper':'Crossroads Epp Mixed Rooibos','CrossRoads Epping Mixed Hamper':'Crossroads Epp mixed hamper','Crossroads Epping Rooibos Hamper 1':'Crossroads Epp Rooibos','Crossroads Epping Coffee Hamper':'Crossroads Epp Ricoffy','Crossroads Hamper Mixed':'Crossroads New hamper Mixed','Pienaar bros Five Roses hamper':'Pienaar Bros five roses','Pienaar bros Rooibos Hamper':'Pienaar Bros Rooibos','Pienaar bros Coffee Hamper':'Pienaar Bros Coffee','Pienaar bros mixed fve roses hamper':'Pienaar Bros mix five roses ','Triple 5 Coffee Hamper':'TRIPLE 5 COFFEE','Distell M Coffee Hamper':'Distell Monis Coffee','Distell M Mix Tea Hamper':'Distell Monis Mix tea','Distell M Rooibos Mix Hamper':'Distell Monis Mix Rbos','Distell M Rooibos Hamper':'Distell Monis rooibos','Distell M Platinum Hamper':'Distell Monis Platinum','Distell M Tea Hamper':'Distell Monis tea','Wheel Collison Mixed Hamper':'Wheel Collision ','Transocean Mixed Hamper 3':'Trans Ocean C3','Transocean Coffee Hamper 2':'Trans Ocean B coffee','Transocean Tea Hamper 1':'Trans Ocean A tea1','Guala Closures Mix Hamper':'Guala Closures','Nederburg Rooibos Hamper':'Nederburg Wines Mixed Rooibos','Nederburg mix Rooibos Hamper':'Nederburg Wines Mixed Rooibos','Nederburg mixed tea':'Nederburg Wines Mixed Tea ','Much Asphalt Mix Hamper':'Much Aspalt Conterman','NSP Unsgaard Mix Hamper':'Nsp Unsgaard'}
# Mpact Atlantis component lines (per unit, from Mpact BOM)
MP={'Mpact Atlantis 500g Sugar':'sugar','Mpact Atlantis Creamer 250g':'creamer','Mpact Atlantis Ricoffy 150g':'ricoffy','Mpact Atlantis Teabags 20\'s':'tea'}
PG={'sugar':20.87/1000,'creamer':39.75/1000,'cremora':92.0/1000,'ricoffy':139.10/1000,'frisco':186.65/1000,'tea':192/1000,'five':280/1000,'rooibos':236.9/1000,'glen':192/1000,'spoon':0.078,'paper':4.54,'tpaper':5.48}
def price(name,g):
    n=name.lower()
    if 'spoon' in n: return PG['spoon']*g
    if 'toilet' in n or 'paper' in n:
        return (PG['tpaper'] if '2 ply' in n else PG['paper'])*g
    if 'five roses' in n: return PG['five']*g
    if 'rooibos' in n or 'freshpak' in n or 'frshpak' in n: return PG['rooibos']*g
    if 'glen' in n: return PG['glen']*g
    if 'tea' in n: return PG['tea']*g
    if 'cremora' in n: return PG['cremora']*g
    if 'creamer' in n: return PG['creamer']*g
    if 'frisco' in n: return PG['frisco']*g
    if 'ricoffy' in n: return PG['ricoffy']*g
    if 'sugar' in n or 'huletts' in n or 'selati' in n or 'white' in n: return PG['sugar']*g
    return None
def per_hamper(tab):
    tot=0
    for n,g in BOM[tab]:
        p=price(n,g)
        if p is None: return None,n
        tot+=p
    return tot,None
MPACT={'sugar':500*PG['sugar'],'creamer':250*PG['creamer'],'ricoffy':150*PG['ricoffy'],'tea':50*PG['tea']}
def hcost(lines):
    """lines (code,desc,qty,sales) -> total sales, cost, priced_sales, rows"""
    rows=[];ps=pc=0;un=[]
    for c,n,q,a in lines:
        cost=None;why=''
        if n in MP: cost=MPACT[MP[n]]*q
        elif n in M:
            t,bad=per_hamper(M[n])
            if t is not None: cost=t*q
            else: why='unpriced ingredient: '+bad
        else: why='no BOM tab'
        rows.append([c,n,q,a,cost,why])
    ps=sum(r[3] for r in rows if r[4] is not None);pc=sum(r[4] for r in rows if r[4] is not None)
    ratio=pc/ps if ps else .65
    tot=sum(r[3] for r in rows)
    for r in rows:
        if r[4] is None: r[4]=r[3]*ratio
    return tot,sum(r[4] for r in rows),ps,pc,ratio,rows

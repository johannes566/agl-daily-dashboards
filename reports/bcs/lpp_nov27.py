# Latest purchase prices ex VAT per unit, from Xero BCS bills 1 Oct to 27 Nov 2026 (190 bills read). Date = bill date of the price used.
import costs as K, hcost as H
NEW={
'006/OMO002/2000':(85.89,'25 Nov Makro'),
'009/RIC003/0250':(59.31,'24 Nov Makro wtd'),
'009/RIC005/0750':(113.00,'24 Nov Makro'),
'009/RIC007/1500':(208.65,'24 Nov Makro'),
'010/CRE001/0750':(45.22,'24 Nov Makro+Giant wtd'),
'023/HUL003/2500':(54.89,'24 Nov Makro'),
'024/FRE001/0080':(43.48,'24 Nov Makro'),
'024/FRE001/0160':(78.22,'24 Nov Makro'),
'024/GLE001/1000':(30.39,'24 Nov Makro'),
'001/T.TIPS/100':(27.82,'24 Nov Makro'),
'009/NES008/0200':(86.91,'24 Nov Makro'),
'009/NES015/0200':(173.87,'24 Nov Makro'),
'004/BIS002/0500':(121.70,'25 Nov Makro'),
'011/ZEB002/0001':(137.34,'24 Nov Makro'),
'023/HUL002/1000':(22.71,'24 Nov Giant wtd'),
'SUGAR/003':(22.71,'mapped to Huletts 1kg 24 Nov'),
'017/DAIRYB/FC1':(99.95,'25 Nov Makro'),
'017/DAIRYB/LF1':(95.31,'24 Nov Makro+Giant wtd'),
'006/RAD001/0300':(41.70,'24 Nov Makro'),
'006/MRM001/0400':(61.72,'24 Nov Makro wtd'),
'006/DOM030/3000':(127.79,'24 Nov Makro'),
'014/CIRO/1000':(165.21,'19 Nov Red Star'),
'006/SUN011/5000':(182.60,'19 Nov Red Star'),
'003/AQU001/3000':(39.99,'19 Nov Red Star'),
'019/TOI001/0048':(218.00,'3 Nov Alpha'),
'019/NAM008/0001':(461.50,'17 Nov Alpha'),
'019/TWINSAVER/2':(262.88,'17 Nov Alpha'),
'019/TOI003/0048':(262.88,'2 Nov Alpha'),
'006/URI001/0001':(284.60,'19 Oct Caprichem, desc-matched (Alpha 18 Nov Scented Blocks 650 NOT used)'),
'TILES/002':(1239.58,'26 Oct OWA'),
'LADDER/003':(1549.84,'19 Oct Fowkes'),
'PAINT/DUL':(999.13,'26 Oct Makro'),
'014/MANTELLI/700':(130.44,'24 Nov Mantelli'),
'MANTELLIS/002':(243.48,'24 Nov Mantelli'),
'MANTELLIS/0020':(243.48,'24 Nov Mantelli'),
'CHOPS01':(1316.96,'1 Oct Fairfield'),
'CHLT0009/08':(740.26,'1 Oct Fairfield'),
'GREEN4':(575.83,'1 Oct Fairfield'),
'013/FIL003/0040':(56.48,'24 Nov Makro'),
'BAMBO0002':(320.87,'25 Nov Banks'),
}
for k,(v,_) in NEW.items(): K.P[k]=v
K.IMAP.update({'TILES/002':'TILES/002','LADDER/003':'LADDER/003'})
# hamper ingredient prices per gram (Nov 24 latest)
H.PG.update({'cremora':45.22/750,'five':121.70/500,'rooibos':78.22/400,'glen':30.39/250})

K.P['LECTURE']=0.0   # lecture income carries no cost of sale in Xero

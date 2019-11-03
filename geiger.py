#!/usr/bin/python

import serial
import requests
import time, datetime

#Hier muessen wir unsere Daten erstmal einfuegen
User="USERNAME"   # User fuer alle Seiten
Passwort="PASSWORD" # Passwort fuer alle Seiten
#Homematics
HMPapa="IPADRESS1"
HMMarvin="IPADRESS2"
#GMCMAP
GMCAccountID="ACCID"
GMCGeigerID="GEIGID"
#Safecast
APISAFECAST="APIKEY"
latitude="lat"
longitude="long"
#uRadmon
uraduserid="fillin"
uradkey="fillin"
uraddeviceid="fillin"

#Verbinungseinstellung
gmc= serial.Serial('/dev/ttyUSB0', 115200, timeout=10) #device Unser Geigerzaehler und wo er angeschlossen ist + Verbindungseinstellung

#Funktionen fuer spaeter

def fun_getCPM(gmc): # Dies ist die Funktion zum auslesen von dem CPM Wert
    gmc.write(b'<GETCPM>>')
    dat = gmc.read(4)
    try:
        gv= ord(dat[0])<< 8 | ord(dat[3])
    except IndexError:
        gv= ord("\x00")
    return gv

def fun_urlopenHM(IP, uSIV=1337): #Funktion zum Aufrufen der HM URLs
    URL='http://%s:8181/blabla.exe?Antwort=dom.GetObject("uSivert").State(%s)'%(IP, uSIV)
    try:
	    HMstatus=requests.post(URL, timeout=5)
            print("\nHomematicIP: %s antwortet %s und %s ")%(IP, HMstatus, HMstatus.content)
    except:
	    print("Beim Uebertragen nach %s gabs einen Fehler!")%(IP)


#Variablen mit 0 fuellen
CPM10M = 0
CPM = 0
uSIV10M = 0
uSIV = 0
Minute = 0
while True:

#Abfrage und umwandlung des Zaehlers / Werte
    CPM=fun_getCPM(gmc) #Mit Hilfe der Funktion getCPM wird der CPM Wert in die Var CPM geschrieben
    print("CPM:{}".format(CPM))
    uSIV= round((CPM *6.5/1000), 2) #usiv wird errechnet und auf 2 Dezimalstellen gerundet
    print("uSv:{}".format(uSIV))

    if Minute == 10:
        print("10Minuten Schlaf sind um - starte Transfer\n\n")
        CPM10M = CPM10M/10 # Hier teilen wir den CPM Wert durch 10 um einen 10Minuten durschnitt zu erhalten
        uSIV10M= uSIV10M/10
        print("Durschnitt CPM der letzen 10Minuten: %s")%(CPM10M)
        print("Durschnitt uSIV der letzen 10Minuten: %s")%(uSIV10M)
        #Hier fragen wir die Uhrzeit ab und schreiben 3 Strings daraus
        datenow=datetime.datetime.now() #Uhrzeit holen
        datestring=(datenow.strftime("%Y-%m-%d%%20%H:%M:%S")) # Uhrzeit als String fuer Var mit Leerzeichen fuer URL
        datestringohne=datenow.strftime('%Y-%m-%dT%H:%M:%S.%f') # UhrzeitString ohne Lerrzeichen
        unixtime=time.time() #Timestamp Unixtime
        print("datenow: %s"%(datenow))
        print(datestringohne)
        print(unixtime)
#Ab hier beginnt dann das ueberbringen der Daten an die einzelenen Endpunkte

        fun_urlopenHM(HMMarvin, uSIV10M) #MarvinCCU bekommt uSiv (ueber Funktion)
        fun_urlopenHM(HMPapa, uSIV10M) # Das gleiche fuer Papa

        try:
            radmonstatus=requests.post('https://radmon.org/radmon.php?user=%s&password=%s&function=submit&datetime=%s&value=%s&unit=CPM HTTP/1.1'%(User, Passwort, datestring, CPM10M), timeout = 10) #Radmon aktualisieren
            print("\nRadmon antwortet %s und %s")%(radmonstatus, radmonstatus.content)
        except:
            print("\nRadmon Uebertragunsfehler")

        try:
            gmcstatus=requests.post('http://www.GMCmap.com/log2.asp?AID=%s&GID=%s&CPM=%s&uSV=%s'%(GMCAccountID, GMCGeigerID, CPM10M, uSIV10M), timeout = 10) #GMCMAP aktualisieren
            print("\nGMCMon antwortet %s und %s")%(gmcstatus, gmcstatus.content)
        except:
            print("\nGMCMon Uebertragunsfehler")


#Safecast ist ein wenig komplizierter, da wir ein Json schicken muessen...
        Safecastpayload = { #Hier schreiben wir das Json zusammen mit allen wichtigen Keys und Werten
            "api_key": APISAFECAST, #unser API-Key
            "value":CPM10M, #unsere CPM
            "unit":"211", # unsere DeviceID / GeraeteID, anzulegen auf der Webseite
            "latitude":latitude, #Unser Ort1
            "longitude":longitude, # UnserOrt2
            "captured_at":datestringohne,
        }
        try:
            responsesafecast = requests.post("https://api.safecast.org/measurements.json", json=Safecastpayload, timeout=10)
            print("\nSafecast antwortet %s und %s")%(responsesafecast, responsesafecast.content)
        except:
            print("\nSafecast Uebertragunsfehler")

#responsesafecasting = requests.post("https://api.ingest.safecast.org", json=Safecastpayload, timeout=5) #Ingest.Safecast funktioniert grade nicht
#print("\nIngest Safecast antwortet %s und %s")%(responsesafecasting, responsesafecasting.content)

        uradheaders= {
            "X-User-id":uraduserid , #is your user ID as presented on the dashboard API tab.
            "X-User-hash":uradkey, #is your user KEY, again on the dashboard.
            "X-Device-id":uraddeviceid, #
        }
        try:
            uradstatus=requests.post('https://data.uradmonitor.com/api/v1/upload/exp/01/%s/0B/%s/10/0x8/0E/1337'%(unixtime, CPM10M), headers=uradheaders, timeout=10) #urad aktualisieren
            print("\nUrad antwortet %s und %s")%(uradstatus, uradstatus.content)
        except:
            print("Fehler beim Datentransfer nach Urad")

#Nach dem erfolgreichen schicken werden die Variablen wieder auf 0 gesetzt um wieder 10 Minuten Pause zu machen.
        Minute = 0
        uSIV = 0
        CPM10M = 0
    else:
        Minute=Minute+1
        time.sleep(60)
        print("Schlafzeit %s von 10Minuten")%(Minute)
        CPM10M = CPM10M + CPM # Bei jedem der 10 Durchlaeufe wird der aktuelle Wert addiert um spaeter dann den Durschnitt zu errechnen
        uSIV10M = uSIV10M + uSIV
        print("Aktuelle DurschnittsCPM: %s / %s")%(CPM10M, Minute)
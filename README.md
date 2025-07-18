# TopDNS
Dynamic DNS with Tophost
<img width="225" height="224" alt="DDNSTophost" src="https://github.com/user-attachments/assets/a1535ae5-cf9e-4288-a199-457a43245138" />

Questo script permette di aggiornare i record A DNS presenti nel cpanel del provider Tophost direttamente da riga di comando, senza utilizzare un browser.
Supporta opzioni per l'esecuzione direttamente da riga di comando, oppure tramite file di configurazione. Effettua inoltre, se la relativa sezione è presente e impostata, l'invio di una mail a operazioni eseguite.

_Si raccomanda di non abusare dello script, cercando di ridurre al minimo le richieste automatizzate inviate al cpanel. In caso contrario è possibile essere bannati via IP, temporaneamente o definitivamente, dal cpanel, o ancor peggio ritrovarsi senza possibilità di usufruire di Tophost per violazione dei termini di servizio..._

## Utilizzo da riga di comando
```
/opt/topdns/topdns.py --help
usage: topdns.py [-h] [--config CONFIG] [--ip IP] [--resolveonly] [--quiet] [username] [password] [records]

Aggiorna record DNS su Tophost

positional arguments:
  username         Username per login
  password         Password per login
  records          Record DNS da aggiornare, separati da virgola (es. esx1,esx2)

options:
  -h, --help       show this help message and exit
  --config CONFIG  Percorso al file di configurazione INI
  --ip IP          Indirizzo IP da impostare (se omesso, usa l'IP pubblico)
  --resolveonly    Esegui solo la risoluzione DNS dei record (nessuna modifica)
  --quiet          Sopprime l'output su stdout
```

## Esempio di file di configurazione

```
[general]
username = dominio.ext
password = cpanel_password
custom_dns = 217.64.201.170,95.174.18.147

[a]
records = www,files,test

[mail]
from = me@email.com
to = you@email.com
smtp_server = mail.server.com
smtp_port = 587
smtp_user = username
smtp_password = password

```

Se non vengono specificati, vengono utilizzati i DNS sopraindicati per la risoluzione dei record DNS.
Gli IP corrispondono a ns1.th.seeweb.it e ns2.th.seeweb.it . Essendo quelli di Tophost, sono i primi a ricevere la modifica (propagazione immediata)

La sezione [mail] è facoltativa.
E' possibile scegliere (variabile interna allo script) se inviare sempre la mail col report o solo in caso di aggiornamento dei record. Questo è particolarmente utile se di decidesse di impostare lo script per una esecuzione periodica mediante cron.

Si raccomanda di non scendere sotto i 5 minuti tra una esecuzione e l'altra per evitare ban temporanei o permanenti.

_E si, questo script è stato scritto con l'aiuto dell'AI..._

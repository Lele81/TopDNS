#!/usr/bin/env python3

import requests
import argparse
import sys
import dns.resolver
import time
import configparser
import smtplib
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
from io import StringIO

# Imposta a True per inviare email sempre, False solo se ci sono modifiche DNS
always_mail = False

# Buffer di output
output_buffer = StringIO()

# Flag quiet
QUIET_MODE = False


def log(msg):
    output_buffer.write(msg + '\n')
    if not QUIET_MODE:
        print(msg)


def req(msg):
    # log(f"REQ: {msg}")
    log(f"{msg}")
    time.sleep(0.5)


def get_public_ip():
    try:
        req("Rilevo IP pubblico via ipify...")
        response = requests.get("https://api.ipify.org", timeout=5)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        log(f"❌ Errore nel rilevamento dell'IP pubblico: {e}")
        sys.exit(2)


def resolve_record(record, expected_ip, dominio, resolver):
    fqdn = f"{record}.{dominio}"
    try:
        answers = resolver.resolve(fqdn, 'A')
        resolved_ips = [rdata.to_text() for rdata in answers]
        if expected_ip in resolved_ips:
            log(f"✅ {fqdn} → {resolved_ips} (OK)")
            return True
        else:
            log(f"❌ {fqdn} → {resolved_ips} (manca {expected_ip})")
            return False
    except Exception as e:
        log(f"❌ Errore nella risoluzione DNS per {fqdn}: {e}")
        return None


def invia_mail(subject, body, mail_config):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = mail_config["from"]
    msg["To"] = mail_config["to"]

    try:
        server = smtplib.SMTP(mail_config["smtp_server"], int(mail_config["smtp_port"]))
        server.starttls()
        server.login(mail_config["smtp_user"], mail_config["smtp_password"])
        server.send_message(msg)
        server.quit()
        log("📧 Email inviata con successo.")
    except Exception as e:
        log(f"❌ Errore invio email: {e}")


def main():
    global QUIET_MODE

    parser = argparse.ArgumentParser(description="Aggiorna record DNS su Tophost")
    parser.add_argument("--config", help="Percorso al file di configurazione INI")
    parser.add_argument("username", nargs="?", help="Username per login")
    parser.add_argument("password", nargs="?", help="Password per login")
    parser.add_argument("records", nargs="?", help="Record DNS da aggiornare, separati da virgola (es. esx1,esx2)")
    parser.add_argument("--ip", help="Indirizzo IP da impostare (se omesso, usa l'IP pubblico)")
    parser.add_argument("--resolveonly", action="store_true", help="Esegui solo la risoluzione DNS dei record (nessuna modifica)")
    parser.add_argument("--quiet", action="store_true", help="Sopprime l'output su stdout")
    args = parser.parse_args()

    QUIET_MODE = args.quiet

    username = password = None
    record_list = []
    ip_forzato = args.ip
    mail_config = None

    if args.config:
        config = configparser.ConfigParser()
        config.read(args.config)

        general = config["general"]
        username = general["username"]
        password = general["password"]
        custom_dns = general.get("custom_dns", "217.64.201.170,95.174.18.147")
        custom_dns_list = [ip.strip() for ip in custom_dns.split(",") if ip.strip()]

        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = custom_dns_list

        record_list = [r.strip() for r in config["a"]["records"].split(",") if r.strip()]
        mail_config = config["mail"]
    else:
        if not (args.username and args.password and args.records):
            print("❌ Errore: specificare username, password e records o usare --config.")
            sys.exit(1)
        username = args.username
        password = args.password
        record_list = [r.strip() for r in args.records.split(",") if r.strip()]
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = ["217.64.201.170", "95.174.18.147"]
        mail_config = None

    subject = f"Aggiornamento record DNS Tophost: dominio {username}"
    dominio = username

    if not ip_forzato:
        ip_pubblico = get_public_ip()
    else:
        ip_pubblico = ip_forzato

    log(f"\n🎯 IP da impostare: {ip_pubblico}")

    records_da_modificare = []
    for record in record_list:
        risultato = resolve_record(record, ip_pubblico, dominio, resolver)
        if risultato is None:
            log(f"⚠️ Salto {record}: errore DNS")
        elif risultato:
            log(f"ℹ️ Salto {record}: già aggiornato")
        else:
            records_da_modificare.append(record)

    if args.resolveonly:
        log("\nℹ️ Risoluzione completata (--resolveonly attivo). Nessuna operazione effettuata.")
        if mail_config and (always_mail or records_da_modificare):
            invia_mail(subject, output_buffer.getvalue(), mail_config)
        return

    if not records_da_modificare:
        log("\n✅ Tutti i record sono già aggiornati. Nessuna modifica necessaria.")
        if mail_config and (always_mail or records_da_modificare):
            invia_mail(subject, output_buffer.getvalue(), mail_config)
        return

    log(f"\n🔧 Record da modificare: {records_da_modificare}")

    url = "https://cp.tophost.it/dns"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/115.0.0.0 Safari/537.36"
    }
    session = requests.Session()

    req("GET /dns (iniziale)")
    try:
        response = session.get(url, headers=headers, timeout=10)
    except Exception as e:
        log(f"❌ Errore: {e}")
        sys.exit(1)
    phpsessid = session.cookies.get("PHPSESSID")

    login_payload = {"user": username, "pass": password}
    req("POST /x-login")
    session.post("https://cp.tophost.it/x-login", data=login_payload, headers=headers)

    req("GET /x-httpsstatus")
    session.get("https://cp.tophost.it/x-httpsstatus", headers=headers)
    nodo_cookie = session.cookies.get("nodo")

    req("GET /dns (con cookie)")
    dns_response = session.get("https://cp.tophost.it/dns", headers=headers)
    soup = BeautifulSoup(dns_response.text, "html.parser")

    td_elements = soup.find_all("td", id=lambda x: x and x.startswith("name-"))

    for record in records_da_modificare:
        record_id = None
        for td in td_elements:
            if td.text.strip() == record:
                record_id = td['id'].replace("name-", "")
                break
        if not record_id:
            log(f"⚠️ Record {record} non trovato nella pagina.")
            continue
        value_td = soup.find("td", id=f"value-{record_id}")
        ip_value = value_td.text.strip() if value_td else None

        log(f"\n🔁 Modifico {record} (ID: {record_id}, vecchio IP: {ip_value})")

        mod_payload = {
            "record": record_id,
            "value": ip_pubblico,
            "valueo": ip_value
        }

        req(f"POST /x-dns-mod ({record})")
        mod_response = session.post("https://cp.tophost.it/x-dns-mod", data=mod_payload, headers=headers)
        try:
            resp_json = mod_response.json()
        except Exception:
            log(f"⚠️ Risposta non valida per {record}")
            continue

        if "msg" in resp_json and "aggiornato" in resp_json["msg"].lower():
            log(f"✅ {record} aggiornato correttamente.")
            log(f"🆔 Nuovo ID: {resp_json.get('recordnewid', 'N/A')}")
        else:
            log(f"❌ Modifica fallita per {record}. Messaggio: {resp_json.get('msg', 'N/A')}")

    if mail_config and (always_mail or records_da_modificare):
        invia_mail(subject, output_buffer.getvalue(), mail_config)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT — verifica che il verdetto di `verify.ps1` sia supportato da una run reale.

Il problema che risolve: un modello puo' *scrivere* una riga `VERIFY_OK |
passed=538 ...` senza aver eseguito nulla (copiandola da un report o
riportandola a memoria). Il file di verdetto, da solo, non basta: serve la
prova che corrisponda a una run registrata nella telemetria.

Il controllo e' puramente meccanico:
  1. `verdict.txt` esiste e contiene una riga `VERIFY_OK` o `VERIFY_FAIL`;
  2. l'ultima riga di `metrics.jsonl` ha lo stesso `status`;
  3. i conteggi `passed`/`failed` del verdetto coincidono con la telemetria;
  4. la run e' recente (non piu' vecchia di `-MaxAgeMin`, default 30).

Uso:
    audit_verdict.py [--root <radice>] [--max-age-min 30]

Exit code: 0 = AUDIT_OK, 1 = AUDIT_FAIL (con motivo), 2 = errore d'uso.
"""

import argparse
import datetime
import json
import os
import sys


def _read_text(path):
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def _parse_verdict(text):
    """(status, campi) dalla riga di verdetto. None se non e' una riga valida."""
    if not text:
        return None
    line = ""
    for candidate in text.splitlines():
        candidate = candidate.strip()
        if candidate.startswith("VERIFY_OK") or candidate.startswith("VERIFY_FAIL"):
            line = candidate
    if not line:
        return None
    status = "OK" if line.startswith("VERIFY_OK") else "FAIL"
    fields = {}
    for chunk in line.split("|")[1:]:
        chunk = chunk.strip()
        if "=" in chunk:
            key, value = chunk.split("=", 1)
            fields[key.strip()] = value.strip()
    return status, fields, line


def _last_metric(path):
    if not os.path.isfile(path):
        return None
    last = None
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            try:
                last = json.loads(raw)
            except ValueError:
                continue
    return last


def main():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--max-age-min", type=float, default=30.0)
    parser.add_argument("--expect-tag", default="",
                        help="task tag atteso: rifiuta un verdetto di una run precedente")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    verdict_path = os.path.join(root, ".opencode", "verdict.txt")
    metrics_path = os.path.join(root, ".opencode", "metrics.jsonl")

    verdict_text = _read_text(verdict_path)
    if verdict_text is None:
        print("AUDIT_FAIL | reason=NO_VERDICT_FILE | path={0}".format(verdict_path))
        return 1

    parsed = _parse_verdict(verdict_text)
    if parsed is None:
        print("AUDIT_FAIL | reason=BAD_VERDICT_FORMAT | path={0}".format(verdict_path))
        return 1
    status, fields, line = parsed

    metric = _last_metric(metrics_path)
    if metric is None:
        print("AUDIT_FAIL | reason=NO_TELEMETRY | path={0}".format(metrics_path))
        return 1

    # 2. lo status deve coincidere
    if metric.get("status") != status:
        print("AUDIT_FAIL | reason=STATUS_MISMATCH | verdict={0} | telemetry={1}".format(
            status, metric.get("status")))
        return 1

    # 2b. il nonce di run deve coincidere: un verdetto scritto a mano non puo'
    # conoscere il nonce generato dalla run che lo ha prodotto.
    verdict_run = fields.get("run")
    telemetry_run = metric.get("run_id")
    if not verdict_run or not telemetry_run:
        print("AUDIT_FAIL | reason=NO_RUN_ID | verdict_run={0} | telemetry_run={1}".format(
            verdict_run, telemetry_run))
        return 1
    if verdict_run != telemetry_run:
        print("AUDIT_FAIL | reason=RUN_MISMATCH | verdict_run={0} | telemetry_run={1}".format(
            verdict_run, telemetry_run))
        return 1

    # 3. i conteggi devono coincidere
    for key in ("passed", "failed"):
        if key in fields:
            try:
                claimed = int(fields[key])
            except ValueError:
                print("AUDIT_FAIL | reason=BAD_COUNT | field={0} | value={1}".format(key, fields[key]))
                return 1
            recorded = metric.get(key)
            if recorded is None:
                print("AUDIT_FAIL | reason=NO_TELEMETRY_COUNT | field={0}".format(key))
                return 1
            if claimed != int(recorded):
                print("AUDIT_FAIL | reason=COUNT_MISMATCH | field={0} | verdict={1} | telemetry={2}".format(
                    key, claimed, recorded))
                return 1

    # 3b. il task tag deve essere quello atteso: un verdetto di una run
    # precedente (stessi conteggi, run diverso) non vale per questa delega.
    if args.expect_tag:
        verdict_tag = fields.get("task")
        telemetry_tag = metric.get("task")
        if verdict_tag != args.expect_tag or telemetry_tag != args.expect_tag:
            print("AUDIT_FAIL | reason=TAG_MISMATCH | expected={0} | verdict={1} | telemetry={2}".format(
                args.expect_tag, verdict_tag, telemetry_tag))
            return 1

    # 4. la run deve essere recente
    ts = metric.get("ts")
    if not ts:
        print("AUDIT_FAIL | reason=NO_TIMESTAMP")
        return 1
    try:
        when = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        print("AUDIT_FAIL | reason=BAD_TIMESTAMP | ts={0}".format(ts))
        return 1
    age = (datetime.datetime.now() - when).total_seconds() / 60.0
    if age > args.max_age_min:
        print("AUDIT_FAIL | reason=STALE | age_min={0:.1f} (max {1})".format(age, args.max_age_min))
        return 1

    print("AUDIT_OK | status={0} | passed={1} | failed={2} | age_min={3:.1f} | verdict={4}".format(
        status, metric.get("passed"), metric.get("failed"), age, line))
    return 0


if __name__ == "__main__":
    sys.exit(main())

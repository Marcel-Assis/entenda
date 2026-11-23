"""Manual discovery of Câmara proposals within a bounded presentation window."""

import argparse
import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import psycopg
from psycopg.types.json import Jsonb

BASE = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
MAX_BODY = 2 * 1024 * 1024
FIELDS = ("siglaTipo", "codTipo", "numero", "ano", "ementa", "dataApresentacao",
          "statusProposicao")


class PageError(ValueError):
    pass


class CursorChanged(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


@dataclass
class Response:
    url: str
    fetched_at: datetime
    status: int | None = None
    body: bytes | None = None
    error: str | None = None
    retry_after: str | None = None


def request(url):
    now = datetime.now(timezone.utc)
    try:
        try:
            response = build_opener(NoRedirect()).open(
                Request(url, headers={"Accept": "application/json"}), timeout=10
            )
        except HTTPError as error:
            response = error
        with response:
            body = response.read(MAX_BODY + 1)
            return Response(url, now, response.code,
                            body if len(body) <= MAX_BODY else None,
                            retry_after=response.headers.get("Retry-After"))
    except (OSError, URLError) as error:
        return Response(url, now, error=type(error).__name__)


def retry_delay(response, attempt):
    if response.retry_after:
        try:
            return max(0, int(response.retry_after))
        except ValueError:
            try:
                return max(0, (parsedate_to_datetime(response.retry_after)
                               - datetime.now(timezone.utc)).total_seconds())
            except (ValueError, TypeError):
                pass
    return 2 ** attempt


def fetch(url, observations, transport, sleep):
    for attempt in range(3):
        response = transport(url)
        observations.append(response)
        status = response.status
        retryable = status is None or status == 429 or 500 <= status <= 599
        if not retryable or attempt == 2:
            return response
        delay = retry_delay(response, attempt)
        if delay > 10:
            return response
        sleep(delay)


def payload(response):
    if response.status != 200 or response.body is None:
        raise PageError(f"HTTP {response.status or response.error}, or missing response body")
    try:
        document = json.loads(response.body)
    except (ValueError, RecursionError) as error:
        raise PageError("invalid_json") from error
    if not isinstance(document, dict):
        raise PageError("invalid_envelope")
    return document


def page_url(scope, page):
    return BASE + "?" + urlencode(sorted({**scope, "pagina": page}.items()))


def page_number(url, scope):
    target = urlsplit(url)
    origin = urlsplit(BASE)
    if (target.scheme, target.netloc, target.path) != (origin.scheme, origin.netloc, origin.path):
        raise PageError("invalid_pagination_origin")
    query = parse_qsl(target.query, keep_blank_values=True)
    params = dict(query)
    page = params.pop("pagina", "")
    if (target.fragment or len(query) != len(params) + 1 or params != scope
            or not page.isascii() or not page.isdecimal() or len(page) > 9 or int(page) < 1):
        raise PageError("invalid_pagination_scope")
    return int(page)


def parse_page(response, scope):
    document = payload(response)
    items, links = document.get("dados"), document.get("links")
    if (not isinstance(items, list) or not isinstance(links, list)
            or len(items) > int(scope["itens"])):
        raise PageError("invalid_page")
    current = page_number(response.url, scope)
    next_links = [link.get("href") for link in links
                  if isinstance(link, dict) and link.get("rel") == "next"]
    if not next_links:
        return items, None, current
    if len(next_links) != 1 or not isinstance(next_links[0], str):
        raise PageError("invalid_next_link")
    if page_number(next_links[0], scope) != current + 1:
        raise PageError("non_sequential_page")
    if not items:
        raise PageError("empty_page_with_next")
    return items, next_links[0], current


def official_id(item):
    value = item.get("id") if isinstance(item, dict) else None
    return value if type(value) is int and 0 < value < 2**63 else None


def in_scope(item, scope):
    try:
        presented = datetime.fromisoformat(item["dataApresentacao"]).date().isoformat()
    except (KeyError, TypeError, ValueError):
        return False
    return item.get("siglaTipo") == "PL" and (
        scope["dataApresentacaoInicio"] <= presented <= scope["dataApresentacaoFim"]
    )


def fetch_detail(proposal_id, observations, transport, sleep, scope=None):
    detail = fetch(f"{BASE}/{proposal_id}", observations, transport, sleep)
    if detail.status == 404:
        return detail, None, "detail_not_found"
    if detail.status != 200 or detail.body is None:
        raise PageError(f"detail_failed: {detail.status or detail.error}")
    try:
        record = payload(detail).get("dados")
        if official_id(record) != proposal_id or (scope is not None and not in_scope(record, scope)):
            raise PageError("invalid_detail_item")
        fields = {key: record[key] for key in FIELDS if key in record}
        json.dumps(fields, allow_nan=False, ensure_ascii=False).encode("utf-8")
    except ValueError:
        return detail, None, "invalid_detail_item"
    return detail, fields, None


def store_observation(db, run_id, response):
    digest = None
    if response.body is not None:
        digest = hashlib.sha256(response.body).digest()
        db.execute("INSERT INTO bodies (payload) VALUES (%s) ON CONFLICT DO NOTHING",
                   (response.body,))
    return db.execute("""
        INSERT INTO observations (run_id, url, fetched_at, http_status, body_sha256, transport_error)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (run_id, response.url, response.fetched_at, response.status,
              digest, response.error)).fetchone()[0]


def store_version(db, proposal_id, fields, evidence):
    encoded = json.dumps(fields, sort_keys=True, separators=(",", ":"), allow_nan=False)
    digest = hashlib.sha256(encoded.encode()).digest()
    db.execute("""
        INSERT INTO proposals VALUES ('camara', %s, 1) ON CONFLICT DO NOTHING
        """, (proposal_id,))
    current_version = db.execute("""
        SELECT current_version FROM proposals WHERE source = 'camara' AND official_id = %s FOR UPDATE
        """, (proposal_id,)).fetchone()[0]
    current = db.execute("""
        SELECT normalizer_version, normalized_sha256 FROM proposal_versions
        WHERE source = 'camara' AND official_id = %s AND version = %s
        """, (proposal_id, current_version)).fetchone()
    if current == (1, digest):
        return False
    version = current_version + 1 if current else 1
    db.execute("""
        INSERT INTO proposal_versions VALUES ('camara', %s, %s, %s, 1, %s, %s)
        """, (proposal_id, version, evidence, digest, Jsonb(fields)))
    db.execute("""
        UPDATE proposals SET current_version = %s WHERE source = 'camara' AND official_id = %s
        """, (version, proposal_id))
    return True


def reject_repeated_page(db, run_id, page, items):
    if page == 1 or not items:
        return
    previous = db.execute("""
        SELECT b.payload FROM confirmed_pages AS p
        JOIN observations AS o ON o.id = p.observation_id
        JOIN bodies AS b ON b.sha256 = o.body_sha256
        WHERE p.run_id = %s AND p.cursor_key = %s
        """, (run_id, str(page - 1))).fetchone()
    ids = [official_id(item) for item in items]
    if previous and any(ids):
        previous_ids = [official_id(item) for item in json.loads(previous[0])["dados"]]
        if ids == previous_ids:
            raise PageError("repeated_page")


def lock_checkpoint(db, run_id, cursor):
    row = db.execute("SELECT cursor FROM runs WHERE id = %s FOR UPDATE", (run_id,)).fetchone()
    if row != (cursor,):
        raise CursorChanged("checkpoint avançado por outra execução")


def discover(db, run_id, max_pages, transport=request, sleep=time.sleep):
    run = db.execute("SELECT scope, cursor, state FROM runs WHERE id = %s AND mode = 'discovery'",
                     (run_id,)).fetchone()
    if run is None:
        raise ValueError("execução de descoberta inexistente")
    scope, cursor, state = run
    summary = {"run_id": run_id, "state": state, "pages": 0, "versions": 0, "quarantined": 0}
    for index in range(max_pages):
        if cursor is None:
            break
        observations = []
        versions, quarantine = {}, []
        try:
            page_number(cursor, scope)
            listing = fetch(cursor, observations, transport, sleep)
            items, next_url, current = parse_page(listing, scope)
            reject_repeated_page(db, run_id, current, items)
            for position, item in enumerate(items):
                proposal_id = official_id(item)
                if not proposal_id or not in_scope(item, scope):
                    quarantine.append((listing, position, proposal_id, "invalid_list_item"))
                    continue
                if proposal_id in versions:
                    continue
                detail, fields, reason = fetch_detail(
                    proposal_id, observations, transport, sleep, scope
                )
                if reason:
                    quarantine.append((detail, position, proposal_id, reason))
                else:
                    versions[proposal_id] = (fields, detail)
        except ValueError as error:
            record_failure(db, run_id, cursor, observations)
            return {**summary, "state": "failed", "error": str(error)}

        with db.transaction():
            lock_checkpoint(db, run_id, cursor)
            evidence = {id(response): store_observation(db, run_id, response)
                        for response in observations}
            for proposal_id, (fields, detail) in sorted(versions.items()):
                summary["versions"] += store_version(db, proposal_id, fields, evidence[id(detail)])
            for response, position, proposal_id, reason in quarantine:
                store_quarantine(db, run_id, evidence[id(response)], position, proposal_id, reason)
            db.execute("INSERT INTO confirmed_pages VALUES (%s, %s, %s)",
                       (run_id, str(current), evidence[id(listing)]))
            state = "completed" if next_url is None else (
                "paused" if index + 1 == max_pages else "running"
            )
            db.execute("""
                UPDATE runs SET cursor = %s, state = %s, updated_at = now(),
                    confirmed_pages = confirmed_pages + 1 WHERE id = %s
                """, (next_url, state, run_id))
        summary.update(state=state, pages=summary["pages"] + 1,
                       quarantined=summary["quarantined"] + len(quarantine))
        cursor = next_url
    return summary


def create_run(db, start, end, items):
    scope = {"siglaTipo": "PL", "ordem": "ASC", "ordenarPor": "id", "itens": str(items),
             "dataApresentacaoInicio": start.isoformat(), "dataApresentacaoFim": end.isoformat()}
    return db.execute("""
        INSERT INTO runs (mode, scope, state, cursor)
        VALUES ('discovery', %s, 'running', %s) RETURNING id
        """, (Jsonb(scope), page_url(scope, 1))).fetchone()[0]


def store_quarantine(db, run_id, evidence, position, proposal_id, reason):
    db.execute("""
        INSERT INTO quarantine (run_id, observation_id, item_index, official_id, reason)
        VALUES (%s, %s, %s, %s, %s)
        """, (run_id, evidence, position, proposal_id, reason))


def record_failure(db, run_id, cursor, observations):
    with db.transaction():
        lock_checkpoint(db, run_id, cursor)
        for response in observations:
            store_observation(db, run_id, response)
        db.execute("UPDATE runs SET state = 'failed', updated_at = now() WHERE id = %s",
                   (run_id,))


def create_refresh_run(db, proposal_ids):
    proposal_ids = sorted(set(proposal_ids))
    if not 1 <= len(proposal_ids) <= 100 or any(not 0 < value < 2**63 for value in proposal_ids):
        raise ValueError("informe de 1 a 100 IDs oficiais válidos")
    known = db.execute("""
        SELECT official_id FROM proposals WHERE source = 'camara' AND official_id = ANY(%s)
        ORDER BY official_id
        """, (proposal_ids,)).fetchall()
    if proposal_ids != [row[0] for row in known]:
        raise ValueError("a reconsulta aceita apenas IDs já coletados")
    return db.execute("""
        INSERT INTO runs (mode, scope, state, cursor)
        VALUES ('refresh', %s, 'running', '0') RETURNING id
        """, (Jsonb({"ids": proposal_ids}),)).fetchone()[0]


def refresh(db, run_id, max_items, transport=request, sleep=time.sleep):
    run = db.execute("SELECT scope, cursor, state FROM runs WHERE id = %s AND mode = 'refresh'",
                     (run_id,)).fetchone()
    if run is None:
        raise ValueError("execução de reconsulta inexistente")
    scope, cursor, state = run
    summary = {"run_id": run_id, "state": state, "items": 0, "versions": 0, "quarantined": 0}
    ids = scope["ids"]
    for _ in range(max_items):
        if cursor is None:
            break
        position = int(cursor)
        proposal_id = ids[position]
        observations = []
        try:
            detail, fields, reason = fetch_detail(proposal_id, observations, transport, sleep)
        except PageError as error:
            record_failure(db, run_id, cursor, observations)
            return {**summary, "state": "failed", "error": str(error)}

        next_cursor = str(position + 1) if position + 1 < len(ids) else None
        state = "completed" if next_cursor is None else (
            "paused" if summary["items"] + 1 == max_items else "running"
        )
        with db.transaction():
            lock_checkpoint(db, run_id, cursor)
            for response in observations:
                evidence = store_observation(db, run_id, response)
            if reason:
                store_quarantine(db, run_id, evidence, position, proposal_id, reason)
                summary["quarantined"] += 1
            else:
                summary["versions"] += store_version(db, proposal_id, fields, evidence)
            db.execute("UPDATE runs SET cursor = %s, state = %s, updated_at = now() WHERE id = %s",
                       (next_cursor, state, run_id))
        cursor = next_cursor
        summary.update(state=state, items=summary["items"] + 1)
    return summary


def main():
    parser = argparse.ArgumentParser(description="Coleta e reconsulta manual de proposições da Câmara")
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--max-items", type=int)
    parser.add_argument("--refresh", type=int, nargs="+", metavar="ID")
    parser.add_argument("--items", type=int)
    parser.add_argument("--from", dest="start", type=date.fromisoformat)
    parser.add_argument("--to", dest="end", type=date.fromisoformat)
    parser.add_argument("--resume", type=int)
    args = parser.parse_args()
    if args.max_pages is not None and not 1 <= args.max_pages <= 20:
        parser.error("--max-pages deve estar entre 1 e 20")
    if args.max_items is not None and not 1 <= args.max_items <= 100:
        parser.error("--max-items deve estar entre 1 e 100")
    if args.resume is not None:
        if args.resume < 1 or any(value is not None for value in (args.start, args.end, args.items, args.refresh)):
            parser.error("--resume exige ID positivo e reutiliza o recorte salvo")
    elif args.refresh is not None:
        if any(value is not None for value in (args.start, args.end, args.items, args.max_pages)):
            parser.error("--refresh usa IDs oficiais e --max-items")
    elif args.max_items is not None:
        parser.error("--max-items exige reconsulta")
    elif not (args.start and args.end and args.start <= args.end
              and (args.items is None or 1 <= args.items <= 20)):
        parser.error("informe --from e --to em ordem e --items entre 1 e 20, se indicado")
    dsn = os.environ.get("ENTENDA_DATABASE_URL")
    if not dsn:
        parser.error("defina ENTENDA_DATABASE_URL")
    try:
        with psycopg.connect(dsn, autocommit=True) as db:
            db.execute("SET search_path TO camara_ingestion, pg_catalog")
            if args.resume is not None:
                run_id = args.resume
                row = db.execute("SELECT mode FROM runs WHERE id = %s", (run_id,)).fetchone()
                if row is None:
                    raise ValueError("execução inexistente")
                mode = row[0]
            elif args.refresh is not None:
                mode = "refresh"
                run_id = create_refresh_run(db, args.refresh)
            else:
                mode = "discovery"
                run_id = create_run(db, args.start, args.end, args.items or 2)
            if mode == "refresh" and args.max_pages is not None:
                parser.error("reconsulta usa --max-items")
            if mode == "discovery" and args.max_items is not None:
                parser.error("descoberta usa --max-pages")
            print(json.dumps({"run_id": run_id}), flush=True)
            if mode == "refresh":
                result = refresh(db, run_id, args.max_items or 20)
            else:
                result = discover(db, run_id, args.max_pages or 2)
    except (ValueError, CursorChanged) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result))
    return int(result["state"] == "failed")


if __name__ == "__main__":
    raise SystemExit(main())

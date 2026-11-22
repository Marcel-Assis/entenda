import json
import os
import unittest
from datetime import date, datetime, timezone

import psycopg

from camara import (BASE, CursorChanged, Response, create_refresh_run, create_run,
                    discover, page_url, refresh, select_refresh_run)


class DiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.db = psycopg.connect(os.environ["ENTENDA_TEST_DATABASE_URL"], autocommit=True)
        self.addCleanup(self.db.close)
        self.db.execute("SET search_path TO camara_ingestion, pg_catalog")
        self.db.execute("BEGIN")
        self.addCleanup(self.db.rollback)

    def new_run(self):
        return create_run(self.db, date(2024, 1, 1), date(2024, 1, 31), 2)

    def response(self, url, data=None, links=(), status=200, raw=None):
        body = json.dumps({"dados": data, "links": list(links)}).encode() if raw is None else raw
        return Response(url, datetime.now(timezone.utc), status, body)

    def scope(self, run):
        return self.db.execute("SELECT scope FROM runs WHERE id = %s", (run,)).fetchone()[0]

    def record(self, proposal_id, title="A"):
        return {"id": proposal_id, "ano": 2024, "siglaTipo": "PL", "ementa": title,
                "dataApresentacao": "2024-01-10T18:15"}

    def test_resume_after_retryable_failure_and_idempotence(self):
        run = self.new_run()
        first, second = [page_url(self.scope(run), page) for page in (1, 2)]
        detail_one, detail_two = [f"{BASE}/{proposal}" for proposal in (1, 2)]
        record_one, record_two = self.record(1), self.record(2)
        routes = {
            first: self.response(first, [record_one], [{"rel": "next", "href": second}]),
            second: self.response(second, [record_two]),
            detail_one: self.response(detail_one, record_one),
            detail_two: self.response(detail_two, status=503),
        }

        def discover_routes(run_id):
            return discover(self.db, run_id, 2, routes.__getitem__, lambda _: None)

        result = discover_routes(run)
        self.assertEqual((result["state"], result["pages"]), ("failed", 1))
        self.assertEqual(self.db.execute("SELECT cursor FROM runs WHERE id = %s", (run,)).fetchone(),
                         (second,))
        self.assertEqual(self.db.execute("SELECT count(*) FROM observations WHERE http_status = 503")
                         .fetchone(), (3,))
        routes[detail_two] = self.response(detail_two, record_two)
        self.assertEqual(discover_routes(run)["state"], "completed")
        self.assertEqual(discover_routes(self.new_run())["versions"], 0)
        routes[detail_one] = self.response(detail_one, self.record(1, "B"))
        self.assertEqual(discover_routes(self.new_run())["versions"], 1)
        self.assertEqual(self.db.execute("""
            SELECT fields->>'ementa' FROM proposal_versions WHERE official_id = 1 ORDER BY version
            """).fetchall(), [("A",), ("B",)])

    def test_empty_invalid_and_untrusted_pagination(self):
        for mode in ("empty", "invalid", "external", "repeated", "repeated_items"):
            with self.subTest(mode=mode):
                run = self.new_run()
                first = page_url(self.scope(run), 1)
                second = page_url(self.scope(run), 2)
                if mode == "empty":
                    routes = {first: self.response(first, [])}
                elif mode == "invalid":
                    routes = {first: self.response(first, raw=b"{")}
                else:
                    target = {"external": "https://example.org/", "repeated": first,
                              "repeated_items": second}[mode]
                    routes = {
                        first: self.response(first, [self.record(2)], [{"rel": "next", "href": target}]),
                        second: self.response(second, [self.record(2)]),
                        f"{BASE}/2": self.response(f"{BASE}/2", self.record(2)),
                    }
                result = discover(self.db, run, 2, routes.__getitem__)
                self.assertEqual(result["state"], "completed" if mode == "empty" else "failed")

    def test_quarantine_and_retry(self):
        run = self.new_run()
        first = page_url(self.scope(run), 1)
        target = f"{BASE}/1"
        retries = iter([
            Response(target, datetime.now(timezone.utc), error="TimeoutError"),
            Response(target, datetime.now(timezone.utc), status=429, retry_after="3"),
            self.response(target, status=404),
        ])
        delays = []

        def transport(url):
            if url == first:
                return self.response(first, [self.record(1), {"id": 2}])
            self.assertEqual(url, target)
            return next(retries)

        result = discover(self.db, run, 1, transport, delays.append)
        self.assertEqual((result["state"], result["quarantined"], result["versions"]),
                         ("completed", 2, 0))
        self.assertEqual(delays, [1, 3])

    def test_stale_checkpoint_after_another_worker_commits(self):
        self.db.execute("ROLLBACK")
        run = self.new_run()
        first = page_url(self.scope(run), 1)
        with psycopg.connect(os.environ["ENTENDA_TEST_DATABASE_URL"], autocommit=True) as other:
            other.execute("SET search_path TO camara_ingestion, pg_catalog")

            def advance_checkpoint(url):
                self.assertEqual(url, first)
                result = discover(other, run, 1, lambda target: self.response(target, []))
                self.assertEqual(result["state"], "completed")
                return self.response(url, [])

            try:
                with self.assertRaises(CursorChanged):
                    discover(self.db, run, 1, advance_checkpoint)
                self.assertEqual(self.db.execute(
                    "SELECT confirmed_pages FROM runs WHERE id = %s", (run,)
                ).fetchone(), (1,))
                self.assertEqual(self.db.execute(
                    "SELECT count(*) FROM observations WHERE run_id = %s", (run,)
                ).fetchone(), (1,))
            finally:
                with other.transaction():
                    other.execute("DELETE FROM confirmed_pages WHERE run_id = %s", (run,))
                    other.execute("DELETE FROM observations WHERE run_id = %s", (run,))
                    other.execute("DELETE FROM runs WHERE id = %s", (run,))

    def test_refresh_preserves_batch_and_history(self):
        discovery = self.new_run()
        first = page_url(self.scope(discovery), 1)
        one, two = f"{BASE}/1", f"{BASE}/2"
        routes = {
            first: self.response(first, [self.record(1), self.record(2)]),
            one: self.response(one, self.record(1)),
            two: self.response(two, self.record(2)),
        }
        self.assertEqual(discover(self.db, discovery, 1, routes.__getitem__)["versions"], 2)
        with self.assertRaisesRegex(ValueError, "já coletados"):
            create_refresh_run(self.db, [3])

        run = create_refresh_run(self.db, [2, 1, 2])
        self.assertEqual(self.scope(run), {"ids": [1, 2]})
        corrected = {**self.record(1, "B"), "dataApresentacao": "2023-12-31T12:00"}
        routes[one] = self.response(one, corrected)
        routes[two] = self.response(two, status=503)

        result = refresh(self.db, run, 1, routes.__getitem__)
        self.assertEqual((result["state"], result["versions"]), ("paused", 1))
        result = refresh(self.db, run, 2, routes.__getitem__, lambda _: None)
        self.assertEqual((result["state"], result["items"]), ("failed", 0))
        self.assertEqual(self.db.execute(
            "SELECT cursor FROM runs WHERE id = %s", (run,)
        ).fetchone(), ("1",))

        routes[two] = self.response(two, status=404)
        result = refresh(self.db, run, 2, routes.__getitem__)
        self.assertEqual((result["state"], result["quarantined"]), ("completed", 1))
        self.assertEqual(self.db.execute("""
            SELECT official_id, version, fields->>'ementa'
            FROM proposal_versions ORDER BY official_id, version
            """).fetchall(), [(1, 1, "A"), (1, 2, "B"), (2, 1, "A")])
        self.assertEqual(self.db.execute("""
            SELECT official_id, reason FROM quarantine WHERE run_id = %s
            """, (run,)).fetchall(), [(2, "detail_not_found")])

        result = refresh(self.db, create_refresh_run(self.db, [1]), 1, routes.__getitem__)
        self.assertEqual(result["versions"], 0)
        result = refresh(self.db, run, 1, None)
        self.assertEqual((result["state"], result["items"]), ("completed", 0))

    def test_automatic_refresh_rotates_and_resumes_existing_batch(self):
        self.assertIsNone(select_refresh_run(self.db, 2))
        discovery = self.new_run()
        first, second = [page_url(self.scope(discovery), page) for page in (1, 2)]
        routes = {
            first: self.response(first, [self.record(1), self.record(2)],
                                 [{"rel": "next", "href": second}]),
            second: self.response(second, [self.record(3)]),
        }
        for proposal_id in (1, 2, 3):
            url = f"{BASE}/{proposal_id}"
            routes[url] = self.response(url, self.record(proposal_id))
        self.assertEqual(discover(self.db, discovery, 2, routes.__getitem__)["versions"], 3)

        batch = select_refresh_run(self.db, 2)
        self.assertEqual(self.scope(batch), {"automatic": True, "ids": [1, 2]})
        self.assertEqual(refresh(self.db, batch, 1, routes.__getitem__)["state"], "paused")
        self.assertEqual(select_refresh_run(self.db, 1), batch)

        target = f"{BASE}/2"
        routes[target] = self.response(target, status=503)
        self.assertEqual(refresh(self.db, batch, 1, routes.__getitem__, lambda _: None)["state"],
                         "failed")
        self.assertEqual(select_refresh_run(self.db, 1), batch)
        self.assertEqual(self.db.execute("""
            SELECT official_id FROM proposals WHERE last_refresh_at IS NOT NULL
            """).fetchall(), [(1,)])

        routes[target] = self.response(target, status=404)
        result = refresh(self.db, batch, 1, routes.__getitem__)
        self.assertEqual((result["state"], result["quarantined"]), ("completed", 1))
        second_batch = select_refresh_run(self.db, 2)
        self.assertEqual(self.scope(second_batch)["ids"], [1, 3])
        self.assertEqual(refresh(self.db, second_batch, 2, routes.__getitem__)["state"], "completed")
        self.assertEqual(self.scope(select_refresh_run(self.db, 1))["ids"], [2])

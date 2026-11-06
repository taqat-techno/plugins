"""Offline tests for skills/dev-env-cleanup/scripts/plan.py (pure planning logic).

Every keep-list rule gets a case, plus orphan detection, the unreachable-cluster brake,
the odoo-local merge (env-doctor's keep-list wins), plan-id tamper/age checks and emit.
"""
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "dev-env-cleanup" / "scripts"))
import plan as P  # noqa: E402

NOW = 1_800_000_000
DAY = 86400
OLD = NOW - 60 * DAY
NEW = NOW - 1 * DAY
MB = 1024 ** 2
GB = 1024 ** 3
H = "/home/dev"


def rows(*recs):
    return "\n".join("\t".join(str(x) for x in r) for r in recs)


def base(*extra):
    return rows(
        ("meta", "now", NOW), ("meta", "home", H), ("meta", "host", "box"), ("meta", "user", "dev"),
        ("meta", "distro", "Ubuntu"),
        ("df", "/", 60 * GB, 1000 * GB),
        ("cluster", "16", "main", "5432", "online", "socket"),
        ("conf", f"{H}/.config/shop/odoo.wsl.conf", OLD, "shop", "5432", "127.0.0.1", "odoo", f"{H}/.local/share/odoo/shop", "", "^shop$"),
        ("conf", f"{H}/.config/shop/lane-a.conf", OLD, "shop_lane_a", "5432", "127.0.0.1", "odoo", f"{H}/.local/share/odoo/shop", "", ""),
        ("db", "5432", "postgres", 8 * MB, 1, 0, 0, 0),
        ("db", "5432", "shop", 2 * GB, 0, OLD, OLD, 1),
        ("db", "5432", "shop_lane_a", 300 * MB, 0, OLD, OLD, 1),
        ("db", "5432", "big_copy", 3 * GB, 0, OLD, 0, 1),
        ("db", "5432", "busy_one", 50 * MB, 2, OLD, 0, 1),
        ("db", "5432", "fresh_one", 50 * MB, 0, NEW, 0, 1),
        ("db", "5432", "tpl_fast", 80 * MB, 0, OLD, 0, 1),
        ("db", "5432", "pinned_db", 80 * MB, 0, OLD, 0, 1),
        ("db", "5432", "django_app", 40 * MB, 0, OLD, 0, 0),
        ("db", "5432", "nosignal", 40 * MB, 0, 0, 0, 1),
        ("ref", "tpl_fast", f"{H}/.config/shop/fast/tpl.env"),
        ("keep", "pinned_*"),
        ("filestore", f"{H}/.local/share/odoo/shop", "shop", 500 * MB, OLD),
        ("filestore", f"{H}/.local/share/odoo/shop", "shop_lane_a", 100 * MB, OLD),
        ("filestore", f"{H}/.local/share/odoo/shop", "gone_db", 70 * MB, OLD),
        ("filestore", f"{H}/.local/share/odoo/shop", "gone_recent", 70 * MB, NEW),
        ("datadir", f"{H}/.local/share/Odoo/oldcluster", 900 * MB, OLD),
        ("filestore", f"{H}/.local/share/Odoo/oldcluster", "ancient", 800 * MB, OLD),
        ("path", "tmp", f"{H}/tmp/old_work", 2 * GB, OLD),
        ("path", "tmp", f"{H}/tmp/today", 1 * GB, NEW),
        ("path", "cache", f"{H}/.cache/pip", 700 * MB, OLD),
        ("path", "cache", f"{H}/.cache/JetBrains", 5 * GB, OLD),
        ("journal", "782.0M"),
        ("vhdx", "Ubuntu", r"C:\wsl\ext4.vhdx", 140 * GB),
        *extra,
    )


def build(text, **kw):
    planner = P.Planner(P.parse_records(text), **kw).build()
    return planner, P.to_plan(planner)


def by_target(plan):
    return {i["target"]: i for i in plan["items"]}


def kept(plan):
    return {k["target"]: k["reason"] for k in plan["keep"]}


def test_keep_rules():
    _, plan = build(base())
    k = kept(plan)
    assert "system database" in k["postgres@5432"]
    assert "main database of" in k["shop@5432"]
    assert "open connection" in k["busy_one@5432"]
    assert "active" in k["fresh_one@5432"]
    assert "tool state file" in k["tpl_fast@5432"]
    assert "keep.txt" in k["pinned_db@5432"]
    items = by_target(plan)
    for name in ("postgres", "shop", "busy_one", "fresh_one", "tpl_fast", "pinned_db"):
        assert f"{name}@5432" not in items


def test_drops_and_backup_rule():
    _, plan = build(base())
    items = by_target(plan)
    lane = items["shop_lane_a@5432"]
    assert lane["action"] == "drop" and lane["backup"] is False      # small inactive Odoo dev copy
    assert "lane-a.conf" in lane["reason"]
    assert items["big_copy@5432"]["backup"] is True                  # >= 1 GiB
    assert items["django_app@5432"]["backup"] is True                # not Odoo: origin unknown
    assert items["nosignal@5432"]["backup"] is True                  # no activity signal at all
    _, plan_all = build(base(), backup_all=True)
    assert by_target(plan_all)["shop_lane_a@5432"]["backup"] is True


def test_dbfilter_of_main_conf_protects_matching_dbs():
    _, plan = build(base(("db", "5432", "shop", 1, 0, OLD, OLD, 1)))
    assert "shop@5432" in kept(plan)


def test_filestores_paired_orphan_recent_and_dead_datadir():
    _, plan = build(base())
    items = by_target(plan)
    paired = items[f"{H}/.local/share/odoo/shop/filestore/shop_lane_a"]
    assert paired["depends_on"] == "shop_lane_a@5432" and paired["action"] == "delete"
    assert "orphan" in items[f"{H}/.local/share/odoo/shop/filestore/gone_db"]["reason"]
    assert f"{H}/.local/share/odoo/shop/filestore/gone_recent" in kept(plan)
    assert f"{H}/.local/share/odoo/shop/filestore/shop" not in items       # main DB's filestore
    assert items[f"{H}/.local/share/Odoo/oldcluster"]["kind"] == "datadir"
    # the dead data dir is removed whole; its filestore is not listed twice
    assert f"{H}/.local/share/Odoo/oldcluster/filestore/ancient" not in items


def test_live_conf_data_dir_is_never_a_datadir_item():
    _, plan = build(base(("datadir", f"{H}/.local/share/odoo/shop", 900 * MB, OLD)))
    assert f"{H}/.local/share/odoo/shop" not in by_target(plan)


def test_unreachable_cluster_disables_orphan_checks_and_conf_archive():
    text = base(("cluster", "16", "other", "5434", "online", "unreachable"))
    _, plan = build(text)
    items = by_target(plan)
    assert f"{H}/.local/share/odoo/shop/filestore/gone_db" not in items
    assert f"{H}/.local/share/Odoo/oldcluster" not in items
    assert not [i for i in plan["items"] if i["kind"] == "conf"]
    assert any("could not be inventoried" in n for n in plan["notes"])


def test_tmp_caches_journal_and_conf_archive():
    _, plan = build(base())
    items = by_target(plan)
    assert items[f"{H}/tmp/old_work"]["action"] == "delete"
    assert f"{H}/tmp/today" in kept(plan)
    assert items[f"{H}/.cache/pip"]["action"] == "delete"
    assert items[f"{H}/.cache/JetBrains"]["action"] == "report"
    assert items["systemd journal"]["action"] == "command" and items["systemd journal"]["needs_root"]
    conf = items[f"{H}/.config/shop/lane-a.conf"]
    assert conf["action"] == "archive" and conf["dest"].startswith(f"{H}/.config/shop/_archive_")
    assert f"{H}/.config/shop/odoo.wsl.conf" not in items


def test_vhdx_compaction_is_a_user_command_sized_after_the_plan():
    _, plan = build(base())
    v = [i for i in plan["items"] if i["kind"] == "vhdx"]
    assert len(v) == 1 and v[0]["action"] == "command" and v[0]["needs_admin"]
    assert "compact-wsl.ps1 -Distro Ubuntu" in v[0]["command"]
    # 140 GiB image vs 60 GiB used minus what the plan frees -> well over 80 GiB of slack
    assert v[0]["size_bytes"] > 80 * GB


def test_vhdx_of_other_distro_is_not_matched():
    _, plan = build(base(("vhdx", "docker-desktop", r"C:\d\ext4.vhdx", 140 * GB)))
    assert [i["target"] for i in plan["items"] if i["kind"] == "vhdx"] == [r"C:\wsl\ext4.vhdx"]


def test_scope_db_only():
    _, plan = build(base(), scope="db")
    kinds = {i["kind"] for i in plan["items"]}
    assert "db" in kinds and "vhdx" not in kinds and "cache" not in kinds


def test_running_process_protects_its_db():
    _, plan = build(base(("proc", "123", "999", "python odoo-bin -c x.conf -d big_copy --http-port 8069")))
    assert "running process" in kept(plan)["big_copy@5432"]


def test_odoo_local_merge_keep_list_wins():
    planner = P.Planner(P.parse_records(base())).build()
    odoo = {"plan_id": "odoo-abc", "keep": [{"target": "khair", "reason": "main_db"}],
            "items": [{"kind": "db", "target": "shop", "size_bytes": 1, "reason": "x", "action": "drop", "backup": False},
                      {"kind": "conf", "target": f"{H}/proj/conf/old.conf", "size_bytes": 0, "reason": "dead",
                       "action": "archive", "backup": False},
                      {"kind": "db", "target": "weird", "action": "nuke"}]}
    P.merge_odoo(planner, odoo)
    plan = P.to_plan(planner)
    items = by_target(plan)
    assert "shop" not in items                                    # main DB: env-doctor keeps it
    assert items[f"{H}/proj/conf/old.conf"]["source"] == "odoo-local"
    assert "weird" not in items                                   # unknown action ignored
    assert any("kept by env-doctor" in n for n in plan["notes"])


def test_odoo_local_published_contract_shape():
    """The shape the odoo plugin documents in mcp_local/README.md: runtime-qualified targets,
    its own kind names, optional {"plans": [...]} wrapper, unknown keys ignored."""
    planner = P.Planner(P.parse_records(base())).build()
    odoo = {"plans": [
        {"plan_id": "plan-1", "distro": "Ubuntu", "created_at": "x", "expires_at": "y", "total_bytes": 1,
         "keep": [{"target": "Ubuntu:5432/khair_main", "reason": "main_db of service khair"}],
         "items": [
             {"kind": "scratch_db", "target": "Ubuntu:5432/shop", "size_bytes": 5, "reason": "r", "action": "drop"},
             {"kind": "scratch_db", "target": "Ubuntu:5432/shop_lane_a", "size_bytes": 5, "reason": "r",
              "action": "drop", "backup": False},
             {"kind": "dead_conf", "target": f"Ubuntu:{H}/proj/conf/old.conf", "size_bytes": 0, "reason": "dead",
              "action": "archive"},
             {"kind": "stale_log", "target": f"Ubuntu:{H}/proj/logs/odoo.log", "size_bytes": 9, "reason": "old",
              "action": "delete", "future_key": 1}]},
        {"plan_id": "plan-2", "distro": "Other", "items": [
            {"kind": "scratch_db", "target": "Other:5432/x", "action": "drop"}]}]}
    P.merge_odoo(planner, odoo)
    plan = P.to_plan(planner)
    items = by_target(plan)
    assert "khair_main@5432" in kept(plan)
    assert "shop@5432" not in items                                   # main DB: keep-list wins
    assert items["shop_lane_a@5432"]["source"] == "env-doctor"         # already planned: not duplicated
    conf = items[f"{H}/proj/conf/old.conf"]
    assert conf["kind"] == "conf" and conf["source"] == "odoo-local" and conf["odoo_target"].startswith("Ubuntu:/")
    assert items[f"{H}/proj/logs/odoo.log"]["kind"] == "log"
    assert "x@5432" not in items and any("not merged" in n for n in plan["notes"])


def test_plan_id_is_content_derived_and_emit_refuses_tampering(tmp_path):
    _, plan = build(base())
    _, again = build(base())
    assert plan["plan_id"] == again["plan_id"] and plan["plan_id"].startswith("envdoc-")
    with pytest.raises(SystemExit, match="not this plan's id"):
        P.emit(plan, "envdoc-0000000000", str(tmp_path), now=NOW)
    edited = json.loads(json.dumps(plan))
    edited["items"][0]["target"] = "shop@5432"
    with pytest.raises(SystemExit, match="edited after"):
        P.emit(edited, plan["plan_id"], str(tmp_path), now=NOW)
    with pytest.raises(SystemExit, match="old"):
        P.emit(plan, plan["plan_id"], str(tmp_path), now=NOW + 30 * 3600)


@pytest.mark.parametrize("field,value", [("db", "shop"), ("port", "5999"), ("conn", "tcp:10.0.0.5:pg"),
                                         ("filestore", "/home/u/.local/share/Odoo/filestore/shop")])
def test_emit_refuses_edits_to_hidden_apply_fields(tmp_path, field, value):
    # The approved id must cover the fields the apply scripts use, not only the displayed ones.
    _, plan = build(base())
    edited = json.loads(json.dumps(plan))
    db = next(i for i in edited["items"] if i["kind"] == "db")
    db[field] = value
    with pytest.raises(SystemExit, match="edited after"):
        P.emit(edited, plan["plan_id"], str(tmp_path), now=NOW)


def test_emit_refuses_db_item_whose_target_disagrees(tmp_path):
    _, plan = build(base())
    db = next(i for i in plan["items"] if i["kind"] == "db")
    db["db"] = "shop"
    plan["plan_id"] = P.plan_id_for(plan["items"])  # a consistent id, but db no longer matches target
    with pytest.raises(SystemExit, match="rebuild the plan"):
        P.emit(plan, plan["plan_id"], str(tmp_path), now=NOW)


def test_emit_writes_lists_and_honours_exclusions(tmp_path):
    _, plan = build(base())
    lane = by_target(plan)["shop_lane_a@5432"]
    written = P.emit(plan, plan["plan_id"], str(tmp_path), now=NOW)
    dbs = (tmp_path / "dbs.tsv").read_text(encoding="utf-8").splitlines()
    files = (tmp_path / "files.tsv").read_text(encoding="utf-8").splitlines()
    confs = (tmp_path / "confs.tsv").read_text(encoding="utf-8").splitlines()
    assert written["dbs.tsv"] == len(dbs) and any(l.startswith("5432\tshop_lane_a\t0\t-\t-\t") for l in dbs)
    assert f"delete\t{H}/.local/share/odoo/shop/filestore/shop_lane_a" in files
    assert any(l.startswith(f"archive\t{H}/.config/shop/lane-a.conf\t") for l in confs)
    assert "journalctl --vacuum-size" in (tmp_path / "commands.txt").read_text(encoding="utf-8")
    # leaving the DB out also leaves out the filestore that depends on it
    P.emit(plan, plan["plan_id"], str(tmp_path / "x"), now=NOW, exclude=[lane["id"]])
    files_x = (tmp_path / "x" / "files.tsv").read_text(encoding="utf-8")
    assert "shop_lane_a" not in files_x and "shop_lane_a" not in (tmp_path / "x" / "dbs.tsv").read_text(encoding="utf-8")


def test_tcp_connection_flows_into_db_list(tmp_path):
    text = base().replace("socket", "tcp:127.0.0.1:odoo")
    _, plan = build(text)
    P.emit(plan, plan["plan_id"], str(tmp_path), now=NOW)
    assert "5432\tshop_lane_a\t0\t127.0.0.1\todoo\t" in (tmp_path / "dbs.tsv").read_text(encoding="utf-8")


def test_render_mentions_plan_id_and_nothing_changed():
    _, plan = build(base())
    text = P.render(plan)
    assert plan["plan_id"] in text and "nothing changed yet" in text and "Kept" in text


def test_cli_build_and_show(tmp_path, capsys):
    inv = tmp_path / "inv.tsv"
    inv.write_text(base(), encoding="utf-8")
    assert P.main(["build", "--inventory", str(inv), "--out-dir", str(tmp_path / "plans"), "--now", str(NOW)]) == 0
    files = list((tmp_path / "plans").glob("envdoc-*.json"))
    assert len(files) == 1
    assert P.main(["show", "--plan", str(files[0])]) == 0
    assert "CLEANUP PLAN" in capsys.readouterr().out


def test_parse_size_units():
    assert P.parse_size("782.0M") == int(782.0 * MB)
    assert P.parse_size("1.5G") == int(1.5 * GB)
    assert P.parse_size("12kB") == 12 * 1024
    assert P.parse_size("junk") == 0

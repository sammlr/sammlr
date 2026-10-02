"""Current runtime protections independent of historical private asset archives."""

from datetime import datetime, timedelta, timezone
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'App'
WORK = ROOT / 'Branding/CEOKlaue'
sys.path.insert(0, str(APP))
import webapp
from App.Database.migration_runner import current_version, migrate
from Scripts.predeploy import run_predeploy
from services.notification_history import NotificationHistoryService


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ImageSources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []
        self.ancestors = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        hidden = 'hidden' in attributes or any(item[1] for item in self.ancestors)
        if tag == 'img':
            # The hidden crop dialog is populated only after choosing a new photo.
            if not (hidden and 'data-crop-image' in attributes and 'src' not in attributes):
                self.sources.append(attributes.get('src', ''))
        if tag not in ('area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'):
            self.ancestors.append((tag, hidden))

    def handle_endtag(self, tag):
        for index in range(len(self.ancestors) - 1, -1, -1):
            if self.ancestors[index][0] == tag:
                del self.ancestors[index:]
                break


class ReleaseRuntimeContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='r5-contract-')
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / 'test.db'
        shutil.copyfile(APP / 'Database/sammlr_reference_s00.db', self.database)
        with sqlite3.connect(self.database) as connection:
            migrate(connection, 20)
        webapp.DB = str(self.database)
        webapp.app.config.update(TESTING=True, CSRF_ENABLED=True,
            PROFILE_PORTRAIT_DIR=str(Path(self.temp.name) / 'portraits'))
        self.client = webapp.app.test_client()
        with self.client.session_transaction() as session:
            session['user_id'] = 1

    def test_owner_editor_and_public_profile_without_any_personal_portrait(self):
        self.assertFalse((APP / 'static/profile-sticker/valentin-portrait-source-v1.png').exists())
        response = self.client.post('/profil/sticker/bearbeiten', data={
            'display_name': 'SYNTHETIC', 'country_code': 'DE', 'club_name': '',
            'accent_color': 'purple', 'crop_x': '0', 'crop_y': '0', 'crop_zoom': '1',
        })
        self.assertEqual(302, response.status_code)
        for route in ('/profil', '/profil/sticker/bearbeiten'):
            self.check_portrait_free_page(route)
        with self.client.session_transaction() as session:
            session['user_id'] = 2
        self.check_portrait_free_page('/profil/fixture_user_1')
        self.assertFalse(Path(webapp.app.config['PROFILE_PORTRAIT_DIR']).exists())

    def check_portrait_free_page(self, route):
        response = self.client.get(route)
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        self.assertIn('profile-sticker-photo-viewport', html)
        self.assertNotIn('valentin-portrait', html)
        self.assertIn('class="profile-sticker-portrait"', html)
        self.assertIn('data:image/svg+xml,', html)
        images = ImageSources()
        images.feed(html)
        for source in images.sources:
            self.assertTrue(source, route)
            if source.startswith('/'):
                self.assertEqual(200, self.client.get(source).status_code, source)
            elif source.startswith('data:image/svg+xml,'):
                placeholder = ET.fromstring(unquote(source.split(',', 1)[1]))
                self.assertEqual('{http://www.w3.org/2000/svg}svg', placeholder.tag)
                self.assertEqual(0, len(placeholder))

    def test_current_notifications_paginate_both_ways_without_retention_loss(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        with sqlite3.connect(self.database) as connection:
            connection.execute('DELETE FROM notifications')
            ids = [connection.execute(
                'INSERT INTO notifications(user_id,title,body,is_read,created_at) VALUES (1,?,?,0,?)',
                (f'Fresh {i}', 'Synthetic', (now + timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S')),
            ).lastrowid for i in range(30)]
        pages = [self.client.post(f'/notifications?page={i}').get_data(as_text=True) for i in (1, 2)]
        for html, expected in zip(pages, (list(reversed(ids))[:25], list(reversed(ids))[25:])):
            self.assertEqual(expected, [int(x) for x in re.findall(r'data-notification-id="(\d+)"', html)])
        self.assertIn('method="POST" action="/notifications?page=2"', pages[0])
        self.assertIn('method="POST" action="/notifications?page=1"', pages[1])

    def test_old_read_notifications_expire_between_two_page_opens(self):
        now = datetime(2030, 6, 15, tzinfo=timezone.utc)
        with sqlite3.connect(self.database) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute('DELETE FROM notifications')
            connection.executemany(
                'INSERT INTO notifications(user_id,title,body,is_read,created_at) VALUES (1,?,?,0,?)',
                [(f'Old {i}', 'Synthetic', (now - timedelta(days=40, seconds=i)).strftime('%Y-%m-%d %H:%M:%S')) for i in range(30)],
            )
            connection.commit()
            service = NotificationHistoryService(connection, now_provider=lambda: now)
            first = service.open_page(1, 1)
            second = service.open_page(1, 2)
            self.assertEqual((25, 2), (len(first.items), first.total_pages))
            self.assertEqual((25, 5, 1, False),
                (second.retention_deleted, len(second.items), second.page, second.has_previous))

    def test_synthetic_v7_backup_upgrade_reaches_v20_and_preserves_source_backup(self):
        database = Path(self.temp.name) / 'v7.db'
        shutil.copyfile(APP / 'Database/sammlr_reference_s00.db', database)
        with sqlite3.connect(database) as connection:
            migrate(connection, 7)
            self.assertEqual(7, current_version(connection))
        result = run_predeploy(database, Path(self.temp.name) / 'backups')
        self.assertEqual(7, result['backup_version'])
        self.assertEqual(20, result['database_version'])
        self.assertEqual(list(range(8, 21)), result['applied_migrations'])
        with sqlite3.connect(result['backup_path']) as backup, sqlite3.connect(database) as final:
            self.assertEqual(7, current_version(backup))
            self.assertEqual(20, current_version(final))
            self.assertEqual([('ok',)], final.execute('PRAGMA integrity_check').fetchall())
            self.assertEqual([], final.execute('PRAGMA foreign_key_check').fetchall())


class ReleaseAssetContracts(unittest.TestCase):
    def test_runtime_fonts_and_markers_rebuild_from_safe_derived_glyphs(self):
        spec = importlib.util.spec_from_file_location('r5_runtime_builder', WORK / '05_runtime/build_runtime_assets.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        manifest = json.loads((WORK / '05_runtime/manifest.json').read_text())
        harmony = json.loads((WORK / '04_harmony/manifest.json').read_text())
        self.assertEqual('CEOKlaue Final Master Harmony v1', harmony['version'])
        self.assertEqual(builder.harmony.SELECTIONS, {
            record['character']: tuple(item['variant'] for item in record['alternates'])
            for record in harmony['characters']
        })
        self.assertEqual(10, harmony['selection_markers']['selected_markers'])
        self.assertEqual(-90, harmony['selection_markers']['normalization']['rotation_degrees'])
        prepared = builder.prepared_master()
        with tempfile.TemporaryDirectory(prefix='r5-glyph-build-', dir=ROOT) as directory:
            output = Path(directory)
            with patch.object(builder, 'RUNTIME', output / 'fonts'), patch.object(builder, 'MARKER_RUNTIME', output / 'markers'):
                for alternate, record in enumerate(manifest['runtime']['assets'], 1):
                    path, _ = builder.build_font(alternate, *prepared)
                    self.assertEqual(record['sha256'], digest(path))
                paths, _ = builder.build_runtime_markers(harmony['selection_markers'])
                expected = {Path(v['runtime_asset']).name: v['runtime_asset_sha256']
                    for family in manifest['selection_markers']['families'] for v in family['variants']}
                self.assertEqual(10, len(paths))
                for path in paths:
                    self.assertEqual(expected[path.name], digest(path))
        wordmark = manifest['header_wordmark']
        self.assertEqual(wordmark['asset_sha256'], digest(ROOT / wordmark['asset']))

    def test_product_master_and_import_policy_checks_remain_in_release_gate(self):
        runtime = json.loads((WORK / '05_runtime/manifest.json').read_text())
        harmony = json.loads((WORK / '04_harmony/manifest.json').read_text())
        self.assertEqual(runtime['master']['harmony_manifest_sha256'], digest(WORK / '04_harmony/manifest.json'))
        self.assertEqual(82, len(harmony['characters']))
        self.assertTrue(all(len(record['alternates']) == 3 for record in harmony['characters']))
        policies = {
            'analog-ui-final-source-manifest.json': ('automatic_selection', 'product_integration', 'accepted_82x3_masterset_changed', 'harmony_changed', 'runtime_changed', 'sticker_list_changed', 'sticker_wall_changed'),
            'final-mini-reselection-source-manifest.json': ('automatic_selection', 'harmony_assets_changed', 'runtime_fonts_changed', 'productive_sticker_assets_changed'),
            'final-reselection-source-manifest.json': ('existing_variants_replaced', 'accepted_triple_sets_changed', 'automatic_selection', 'harmony_font_built'),
        }
        for name, keys in policies.items():
            policy = json.loads((WORK / name).read_text())['policy']
            for key in keys:
                self.assertFalse(policy[key], (name, key))
        analog = json.loads((WORK / 'analog-ui-final-source-manifest.json').read_text())['policy']
        self.assertTrue(analog['append_only'])
        self.assertEqual([], analog['product_assets_written'])
        final = json.loads((WORK / 'final-reselection-source-manifest.json').read_text())['policy']
        self.assertEqual([], final['product_assets_written'])

    def test_current_manifest_asset_hashes_do_not_depend_on_any_database_hash(self):
        manifest = json.loads((WORK / '05_runtime/manifest.json').read_text())
        for family in manifest['selection_markers']['families']:
            for record in family['variants']:
                self.assertEqual(record['runtime_asset_sha256'], digest(ROOT / record['runtime_asset']))
        self.assertEqual(manifest['header_wordmark']['asset_sha256'], digest(ROOT / manifest['header_wordmark']['asset']))

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'prepare_sources.py'
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('prepare_sources', SCRIPT)
sources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sources)


class SourceTests(unittest.TestCase):
    def setUp(self):
        workspace = ROOT / 'work' / 'tests'
        workspace.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=workspace)
        self.root = Path(self.temp.name).resolve()
        self.assertTrue(self.root.is_relative_to(workspace.resolve()))
        self.addCleanup(self.temp.cleanup)
        self.books = self.root / 'books'
        self.books.mkdir()
        self.output = self.root / 'normalized'

    def book(self, name, text='第一章 开端\n雨来了。\n第二章 选择\n她留下了。\n第三章 后果\n门开了。\n'):
        path = self.books / name
        path.write_text(text, encoding='utf-8')
        return path

    def run_prepare(self, *inputs, extra=()):
        result = subprocess.run([sys.executable, str(SCRIPT), *map(str, inputs),
                                 '--output', str(self.output), *extra], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
        return json.loads((self.output / 'manifest.json').read_text(encoding='utf-8'))

    def test_identity_survives_new_book_and_rename(self):
        b = self.book('b.txt')
        before = self.run_prepare(self.books)['sources'][0]
        self.book('a.txt', 'Chapter 1\nAnother story.')
        after = next(s for s in self.run_prepare(self.books)['sources'] if s['filename'] == 'b.txt')
        self.assertEqual(before['source_id'], after['source_id'])
        b.rename(self.books / 'renamed.txt')
        self.assertEqual(len(self.run_prepare(self.books)['sources']), 2)

    def test_incremental_and_duplicate_import(self):
        b = self.book('b.txt')
        before = self.run_prepare(b)['sources'][0]
        a = self.book('a.txt', 'Chapter 1\nA different story.')
        result = self.run_prepare(a)
        self.assertEqual(len(result['sources']), 2)
        self.assertIn(before['source_id'], [s['source_id'] for s in result['sources']])
        self.assertEqual(len(self.run_prepare(a)['sources']), 2)

    def test_explicit_revision_preserves_old_text(self):
        b = self.book('b.txt')
        old = self.run_prepare(b)['sources'][0]
        old_text = Path(old['normalized_path']).read_text(encoding='utf-8')
        b.write_text(old_text + '\n终章 回家\n灯亮了。', encoding='utf-8')
        new = self.run_prepare(b, extra=('--source-id', old['source_id']))['sources'][0]
        self.assertEqual(old['source_id'], new['source_id'])
        self.assertNotEqual(old['revision'], new['revision'])
        self.assertEqual(len(new['revisions']), 2)
        self.assertEqual(Path(old['normalized_path']).read_text(encoding='utf-8'), old_text)

    def test_same_name_changed_content_is_not_silently_merged(self):
        b = self.book('b.txt')
        self.run_prepare(b)
        b.write_text('Chapter 1\nEntirely different work.', encoding='utf-8')
        self.assertEqual(len(self.run_prepare(b)['sources']), 2)

    def test_chapter_offsets_and_bom(self):
        b = self.book('b.txt')
        text = b.read_text(encoding='utf-8')
        b.write_bytes(text.encode('utf-16'))
        item = self.run_prepare(b)['sources'][0]
        self.assertEqual(Path(item['normalized_path']).read_text(encoding='utf-8'), text)
        chapters = item['chapters']
        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[1]['start_line'], 3)
        self.assertEqual(text[chapters[1]['start_offset']:chapters[1]['end_offset']], '第二章 选择\n她留下了。\n')

    def test_fullwidth_indented_chapters_preserve_locators(self):
        text = '书籍说明\n\n　　第一章 海岸\n　　船到了。\n\n　　第二章 旧桥\n　　桥断了。\n'
        chapters = sources.chapter_index(text)
        self.assertEqual([c['title'] for c in chapters], ['章前内容', '第一章 海岸', '第二章 旧桥'])
        self.assertEqual(chapters[1]['start_line'], 3)
        self.assertEqual(text[chapters[2]['start_offset']:chapters[2]['end_offset']], '　　第二章 旧桥\n　　桥断了。\n')

    def test_collection_heading_and_prologue_are_indexed(self):
        text = '　　第一集 雾港\n\n　　序章 归船\n　　雾很浓。\n\n　　第一章 信使\n　　有人敲门。\n'
        chapters = sources.chapter_index(text)
        self.assertEqual([c['title'] for c in chapters], ['第一集 雾港', '序章 归船', '第一章 信使'])
        self.assertEqual(chapters[1]['start_line'], 3)

    def test_volume_prefixed_chapters_are_separate_sections(self):
        text = '卷一 初来 第1章 车站\n甲。\n卷一 初来 第2章 火光\n乙。\n卷二 远行 第3章 山口\n丙。\n'
        chapters = sources.chapter_index(text)
        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[2]['title'], '卷二 远行 第3章 山口')
        self.assertEqual(chapters[1]['start_line'], 3)

    def test_body_mentions_of_volumes_are_not_headings(self):
        text = '第一章 海岸\n　　第一卷的六张地图出现时，旧航路重新开放。\n　　卷一的结尾尚未写完。\n第二章 山口\n风来了。\n'
        chapters = sources.chapter_index(text)
        self.assertEqual([c['title'] for c in chapters], ['第一章 海岸', '第二章 山口'])
        self.assertIn('六张地图', text[chapters[0]['start_offset']:chapters[0]['end_offset']])

    def test_adjacent_chinese_chapter_titles_remain_supported(self):
        text = '序章归船\n雾很浓。\n第一章海岸\n船到了。\n第二章旧桥\n桥断了。\n终章归来\n灯亮了。\n'
        chapters = sources.chapter_index(text)
        self.assertEqual([c['title'] for c in chapters], ['序章归船', '第一章海岸', '第二章旧桥', '终章归来'])
        self.assertEqual([c['start_line'] for c in chapters], [1, 3, 5, 7])

    def test_legacy_manifest_keeps_alias_and_existing_work(self):
        self.output.mkdir()
        legacy = self.output / 'book-01-12345678.txt'
        legacy.write_text('Chapter 1\nOld work.', encoding='utf-8')
        manifest = {'sources': [{'source_id': legacy.stem, 'filename': 'old.txt',
                                'format': '.txt', 'normalized_path': str(legacy)}], 'warnings': []}
        (self.output / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        self.book('new.txt')
        result = self.run_prepare(self.books)
        self.assertEqual(len(result['sources']), 2)
        old = next(s for s in result['sources'] if s['filename'] == 'old.txt')
        self.assertIn('book-01-12345678', old['aliases'])
        self.assertTrue(old['source_id'].startswith('src-'))

    def epub(self, missing=False):
        path = self.books / 'story.epub'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('META-INF/container.xml', '<container><rootfiles><rootfile full-path="OEBPS/book.opf"/></rootfiles></container>')
            archive.writestr('OEBPS/book.opf', '<package><manifest><item id="two" href="chapter2.xhtml"/><item id="ten" href="chapter10.xhtml"/></manifest><spine><itemref idref="two"/><itemref idref="ten"/></spine></package>')
            archive.writestr('OEBPS/chapter2.xhtml', '<p>SECOND</p>')
            if not missing:
                archive.writestr('OEBPS/chapter10.xhtml', '<p>TENTH</p>')
        return path

    def test_epub_spine_controls_order(self):
        text = sources.extract_epub(self.epub())
        self.assertLess(text.index('SECOND'), text.index('TENTH'))

    def test_epub_missing_spine_member_reports_error(self):
        with self.assertRaisesRegex(ValueError, 'spine|缺失'):
            sources.extract_epub(self.epub(missing=True))

    def test_no_inputs_does_not_replace_manifest(self):
        self.run_prepare(self.book('b.txt'))
        before = (self.output / 'manifest.json').read_bytes()
        result = subprocess.run([sys.executable, str(SCRIPT), str(self.root / 'missing'),
                                 '--output', str(self.output)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.output / 'manifest.json').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()

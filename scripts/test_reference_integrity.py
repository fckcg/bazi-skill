from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parent.parent


class ReferenceIntegrityTests(unittest.TestCase):
    def test_index_links_exist(self):
        text=(ROOT/'references/interpretation-index.md').read_text(encoding='utf-8')
        for target in re.findall(r"\]\(([^)]+)\)",text):
            with self.subTest(target=target):
                self.assertTrue((ROOT/'references'/target).is_file())

    def test_no_unqualified_guarantees(self):
        strong=re.compile('必有|必然|必定|一定会|一定发生|必发生|必患')
        allowed=re.compile('历史引文|不得|不能|不要|禁止|不应|不宜|❌|反对|未向.*承诺|必有实墙|比劫多必有财官来制')
        for path in (ROOT/'references').rglob('*.md'):
            for i,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
                if strong.search(line):
                    with self.subTest(file=path.name,line=i):
                        self.assertIsNotNone(allowed.search(line))

    def test_no_numeric_accuracy_promises(self):
        for path in (ROOT/'references').rglob('*.md'):
            self.assertIsNone(re.search(r"[0-9]+\s*[%％]",path.read_text(encoding='utf-8')),path.name)

    def test_risky_modes_have_no_personal_prediction_tables(self):
        for name in ['jibing-yuce.md','wuyun-liuqi-bazi.md','tiekou-guize.md','ziwei-bazi-jiaocha.md']:
            text=(ROOT/'references'/name).read_text(encoding='utf-8')
            self.assertNotIn('|---',text,name)
            self.assertNotIn('比例未经验证',text,name)


if __name__ == '__main__':
    unittest.main()
